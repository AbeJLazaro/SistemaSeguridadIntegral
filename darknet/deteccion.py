from IPython.display import display, Javascript, Image
from google.colab.output import eval_js
from google.colab.patches import cv2_imshow
from base64 import b64decode, b64encode
import cv2
import numpy as np
import PIL
import io
import html
import time
import matplotlib.pyplot as plt
import sys
import time
# biblioteca para generar los mensajes a telegram
import mensaje
# import darknet functions to perform object detections
sys.path.append("/content/drive/My Drive/YOLO/darknet")
from darknet import *

network = None
class_names = None
class_colors = None
classesDetected = dict()
registros = list()

def load_model(cfg="cfg/yolov4-csp.cfg",data="cfg/coco.data",weights="yolov4-csp.weights"):
    '''
    load_model: Carga de la red neuronal
    Parámetros
    cfg: archivo de configuracio
    data: archivo de datos para el modelo
    weights: archivo con los pesos de la red

    return ancho y altura de la red
    '''
    global network, class_names, class_colors
    try:
        network, class_names, class_colors = load_network(cfg,data,weights)
    except FileNotFoundError as e:
        print("No se encuentra alguno de los archivos de configuracion")
        raise e
    widthNet = network_width(network)
    heightNet = network_height(network)
    return widthNet,heightNet

# darknet helper function to run detection on image
def darknet_helper(img, width, height):
    '''
    darknet_helper

    Parámetros
    img: imagen sobre la que se detectan objetos
    width: ancho de detección de la red
    height: altura de detección de la red

    return detecciones y radios de redimensionamiento
    '''

    # se crea una "imagen" (tipo wrapper) para darknet con las dimensiones 
    darknet_image = make_image(width, height, 3)
    # se crea una representación rgb de la imagen "img" con cv2
    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    # se redimensiona la imagen con cv2
    img_resized = cv2.resize(img_rgb, (width, height), 
                                    interpolation=cv2.INTER_LINEAR)

    # get image ratios to convert bounding boxes to proper size
    # se obtienen la información de las dimensiones de la imagen
    img_height, img_width, _ = img.shape
    # se calcula el radio de altura y anchura con las dimensiones anteriores y las de 
    # la "imagen de darknet"
    width_ratio = img_width/width
    height_ratio = img_height/height

    # run model on darknet style image to get detections
    # se copia la imagen redimensionada a la imagen para darknet
    copy_image_from_bytes(darknet_image, img_resized.tobytes())
    # se obtiene la información de las detecciones con la red, las clases y la imagen de darknet
    detections = detect_image(network, class_names, darknet_image)
    # se liberta(?) la imagen
    free_image(darknet_image)

    # se retorna las detecciones y los radios de cambio
    return detections, width_ratio, height_ratio

# funciones para trabajar directamente desde Colab con la camara web
# function to convert the JavaScript object into an OpenCV image
def js_to_image(js_reply):
  """
  Params:
          js_reply: JavaScript object containing image from webcam
  Returns:
          img: OpenCV BGR image
  """
  # decode base64 image
  image_bytes = b64decode(js_reply.split(',')[1])
  # convert bytes to numpy array
  jpg_as_np = np.frombuffer(image_bytes, dtype=np.uint8)
  # decode numpy array into OpenCV BGR image
  img = cv2.imdecode(jpg_as_np, flags=1)

  return img

# function to convert OpenCV Rectangle bounding box image into base64 byte string to be overlayed on video stream
def bbox_to_bytes(bbox_array):
  """
  Params:
          bbox_array: Numpy array (pixels) containing rectangle to overlay on video stream.
  Returns:
        bytes: Base64 image byte string
  """
  # convert array into PIL image
  bbox_PIL = PIL.Image.fromarray(bbox_array, 'RGBA')
  iobuf = io.BytesIO()
  # format bbox into png for return
  bbox_PIL.save(iobuf, format='png')
  # format return string
  bbox_bytes = 'data:image/png;base64,{}'.format((str(b64encode(iobuf.getvalue()), 'utf-8')))

  return bbox_bytes

# función para tomar una foto de javascript
def take_photo(quality=0.8):
    '''
    take_photo: Toma una foto usando javascript y la webcam

    Parámetros
    quality: calidad de la imagen

    Return foto
    '''
    js = Javascript('''
        async function takePhoto(quality) {
            const div = document.createElement('div');
            const capture = document.createElement('button');
            capture.textContent = 'Captura';
            div.appendChild(capture);

            const video = document.createElement('video');
            video.style.display = 'block';
            const stream = await navigator.mediaDevices.getUserMedia({video: true});

            document.body.appendChild(div);
            div.appendChild(video);
            video.srcObject = stream;
            await video.play();

            // Resize the output to fit the video element.
            google.colab.output.setIframeHeight(document.documentElement.scrollHeight, true);

            // Wait for Capture to be clicked.
            await new Promise((resolve) => capture.onclick = resolve);

            const canvas = document.createElement('canvas');
            canvas.width = video.videoWidth;
            canvas.height = video.videoHeight;
            canvas.getContext('2d').drawImage(video, 0, 0);
            stream.getVideoTracks()[0].stop();
            div.remove();
            return canvas.toDataURL('image/jpeg', quality);
        }
    ''')
    display(js)

    # get photo data
    data = eval_js('takePhoto({})'.format(quality))
    # get OpenCV format image
    img = js_to_image(data) 

    return img

# funciones para crear el video stream con javascript
# JavaScript to properly create our live video stream using our webcam as input
def video_stream():
  js = Javascript('''
    var video;
    var div = null;
    var stream;
    var captureCanvas;
    var imgElement;
    var labelElement;
    
    var pendingResolve = null;
    var shutdown = false;
    
    function removeDom() {
       stream.getVideoTracks()[0].stop();
       video.remove();
       div.remove();
       video = null;
       div = null;
       stream = null;
       imgElement = null;
       captureCanvas = null;
       labelElement = null;
    }
    
    function onAnimationFrame() {
      if (!shutdown) {
        window.requestAnimationFrame(onAnimationFrame);
      }
      if (pendingResolve) {
        var result = "";
        if (!shutdown) {
          captureCanvas.getContext('2d').drawImage(video, 0, 0, 640, 480);
          result = captureCanvas.toDataURL('image/jpeg', 0.8)
        }
        var lp = pendingResolve;
        pendingResolve = null;
        lp(result);
      }
    }
    
    async function createDom() {
      if (div !== null) {
        return stream;
      }

      div = document.createElement('div');
      div.style.border = '2px solid black';
      div.style.padding = '3px';
      div.style.width = '100%';
      div.style.maxWidth = '600px';
      document.body.appendChild(div);
      
      const modelOut = document.createElement('div');
      modelOut.innerHTML = "<span>Estado:</span>";
      labelElement = document.createElement('span');
      labelElement.innerText = 'Sin informacion';
      labelElement.style.fontWeight = 'bold';
      modelOut.appendChild(labelElement);
      div.appendChild(modelOut);
           
      video = document.createElement('video');
      video.style.display = 'block';
      video.width = div.clientWidth - 6;
      video.setAttribute('playsinline', '');
      video.onclick = () => { shutdown = true; };
      stream = await navigator.mediaDevices.getUserMedia(
          {video: { facingMode: "environment"}});
      div.appendChild(video);

      imgElement = document.createElement('img');
      imgElement.style.position = 'absolute';
      imgElement.style.zIndex = 1;
      imgElement.onclick = () => { shutdown = true; };
      div.appendChild(imgElement);
      
      const instruction = document.createElement('div');
      instruction.innerHTML = 
          '<span style="color: red; font-weight: bold;">' +
          'Da click en este label para terminar la detección</span>';
      div.appendChild(instruction);
      instruction.onclick = () => { shutdown = true; };
      
      video.srcObject = stream;
      await video.play();

      captureCanvas = document.createElement('canvas');
      captureCanvas.width = 640; //video.videoWidth;
      captureCanvas.height = 480; //video.videoHeight;
      window.requestAnimationFrame(onAnimationFrame);
      
      return stream;
    }
    async function stream_frame(label, imgData) {
      if (shutdown) {
        removeDom();
        shutdown = false;
        return '';
      }

      var preCreate = Date.now();
      stream = await createDom();
      
      var preShow = Date.now();
      if (label != "") {
        labelElement.innerHTML = label;
      }
            
      if (imgData != "") {
        var videoRect = video.getClientRects()[0];
        imgElement.style.top = videoRect.top + "px";
        imgElement.style.left = videoRect.left + "px";
        imgElement.style.width = videoRect.width + "px";
        imgElement.style.height = videoRect.height + "px";
        imgElement.src = imgData;
      }
      
      var preCapture = Date.now();
      var result = await new Promise(function(resolve, reject) {
        pendingResolve = resolve;
      });
      shutdown = false;
      
      return {'create': preShow - preCreate, 
              'show': preCapture - preShow, 
              'capture': Date.now() - preCapture,
              'img': result};
    }
    ''')

  display(js)
  
# función que activa el frame sobre el video
def video_frame(label, bbox):
  data = eval_js('stream_frame("{}", "{}")'.format(label, bbox))
  return data

# contador
def objectCheck(detections):
    '''
    Analiza las detecciones generando la información para la base de datos
    
    Parámetros
    detections: información de la predicción
    '''
    lab = []
    for label, confidence, bbox in detections:
        if label not in classesDetected:
            classesDetected[label]= dict()
            classesDetected[label]["time"] = time.time()
            classesDetected[label]["confidence"] = [float(confidence)]
            classesDetected[label]["hour"] = str(time.asctime(time.localtime()))
        else:
            classesDetected[label]["confidence"].append(float(confidence))
        lab.append(label)

    aux = list(classesDetected.keys())
    for name in aux:
        if name not in lab:
            informacion = classesDetected.pop(name)
            ConfProm = sum(informacion["confidence"])/len(informacion["confidence"])
            print("tiempo de detectado de "+name+":",time.time()-informacion["time"])
            # nombre,hora,confianza
            registros.append(name+","+str(informacion["hour"])+","+str(ConfProm)+"\n")
            	
# Escribe en la base de datos          	
def write():
    # función que escribe en la base de datos
    global registros
    with open("registros.csv","a") as n:
        n.writelines(registros)
    registros = list()

# función stream del video
def stream_video_detection(width,height,N,M):
    '''
    Inicia la detección mediante webcam

    Parámetros
    width: ancho de imagenes para la red
    height: altura de imagenes para la red
    N: cada N número de frames se escribe en base de datos
    M: cada M número de frames detectando una clase se envia notificacion 
    '''
    global classesDetected
    classesDetected = dict()
    # start streaming video from webcam
    video_stream()
    # label for video
    label_html = 'Capturing...'
    # initialze bounding box to empty
    bbox = ''

    # contador de frames para base de datos
    FpBD = 0 

    # contadores frames por clase
    cortas = 0
    blancas = 0
    while True:
        FpBD += 1 

        js_reply = video_frame(label_html, bbox)
        if not js_reply:
            break

        # convert JS response to OpenCV Image
        frame = js_to_image(js_reply["img"])

        # create transparent overlay for bounding box
        bbox_array = np.zeros([480,640,4], dtype=np.uint8)

        # call our darknet helper on video frame
        detections, width_ratio, height_ratio = darknet_helper(frame, width, height)

        objectCheck(detections)

        if FpBD>N:
            write()
            FpBD = 0

        if cortas >= M:
            mensaje.send_messages(frame, "Cortas "+str(time.asctime(time.localtime())))
            cortas = 0
        if blancas >= M:
            mensaje.send_messages(frame, "Blancas "+str(time.asctime(time.localtime())))
            blancas = 0
            
        # loop through detections and draw them on transparent overlay image
        for label, confidence, bbox in detections:
            left, top, right, bottom = bbox2points(bbox)
            left, top, right, bottom = int(left * width_ratio), int(top * height_ratio), int(right * width_ratio), int(bottom * height_ratio)
            bbox_array = cv2.rectangle(bbox_array, (left, top), (right, bottom), class_colors[label], 2)
            bbox_array = cv2.putText(bbox_array, "{} [{:.2f}]".format(label, float(confidence)),
                        (left, top - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5,
                        class_colors[label], 2)
            if label == "cortas":
                cortas +=1
            elif label == "blancas":
                blancas +=1

        bbox_array[:,:,3] = (bbox_array.max(axis = 2) > 0 ).astype(int) * 255
        # convert overlay of bbox into bytes
        bbox_bytes = bbox_to_bytes(bbox_array)
        # update bbox so next frame gets new overlay
        bbox = bbox_bytes