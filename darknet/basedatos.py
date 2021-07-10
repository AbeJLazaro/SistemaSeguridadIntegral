def mostrar():
    with open("registros.csv","r") as f:
        datos = f.readlines()

        template = "|{0:^15}|{1:^30}|{2:^20}|"
        print(template.format("Objeto","Fecha","Precision"))
        for registro in datos:
            info = registro.split(",")
            print(template.format(info[0],info[1],info[2]))