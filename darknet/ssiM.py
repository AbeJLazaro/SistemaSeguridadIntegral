import deteccion
import mensaje 
import basedatos

def main(cfg="cfg/yolov4-csp.cfg",data="cfg/coco.data",weights="yolov4-csp.weights"):
    print("Cargando modelo")
    w,h = deteccion.load_model(cfg,data,weights)
    
    while True:
        print("\n"*3)
        print("1.- Comenzar deteccion en tiempo real")
        print("2.- Mostrar registros")
        print("0.- Salir")
        opt = input("Selecciona una opción :D : ")
        if opt == "1":
            N = 20#int(input("¿Después de cuantos fotogramas se Escribirá en la base de datos? : "))
            M = 20#int(input("¿Después de cuantos fotogramas se enviará la notificación? : "))
            deteccion.stream_video_detection(w,h,N,M)
        elif opt == "2":
            basedatos.mostrar()
        else:
            print("Adios :D")
            break
