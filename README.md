# Bot de Python y telegram
Este repositorio muestra la implementacion de bot de telegram usando la libreria telebot de python.




## configuracion

1. Clona este repositorio
2. instala las dependecias usando "pip install -r requiments.txt"
3. crear un bot de telegram con 'BOTFATHER'y obten tu token
4. reemplaza tu token en 'env.py'
5. abre el ejecutable y haz uso del interface








## En cuanto al lanzador

Bienvenido al lanzador del bot.
*este le permitira editar de manera rapida el contenido de su proyecto.

-el boton "inventario" le permite vizualizar su inventario 
(mediante doble click podra modificar los valores de cualquier casillas.)

-el boton "usuarios" le permite vizualizar su lista de usuarios
(mediante doble click podra modificar los valores de cualquier casillas.)


-el boton "iniciar" permitira poner en linea el bot!
*tener claro que no debe existir ninguna instancia activa del mismo bot

-el boton "finalizar" pemitira apagar el bot!
*tener en cuenta que cerrara la misma sesion que abrio el boton iniciar!
*es de importancia vital para el buen funcionamiento y constancia del bot 
el apagarlo antes de realizar cualquier cambio en los archivos origen!'



## En cuanto al bot

Bienvenido al bot.
*este ofrece una interaccion entre el usuario del bot en la app de telegram y los archivos origen de los datos!

-el chat ofrece al usuario distintas utilidades:
    *telegram entrega un identificador unico a cada uno de sus usuarios, es mediante este que reconocemos a cada uno de ellos*

    Saludo: sera el mensaje inicial que se le muestra al usuario, este se compone de una imagen principal y una breve reseña.
        nos mostrara algunos botones en la parte inferior  para continuar a otras funcionalidades.

            

    Registro: el registro se encarga de comprobar en nuestra tabla de usuarios, si existe un usuario con un identificador igual al usuario en linea.
        en caso contrario ofrece al usuario un cuestionario para realizar su registro.

        el usuario quedara archivado en la 'Hoja 3' del archivo excel!
        **Tipo**: la columna 'tipo' de dicha hoja, especifica el rango del usuario.
        cada rango activa y desactiva distintas experiencias del usuario.
    
    Pedido: inicia una linea de acciones que le permiten al usuario iniciar su proceso de pedido.
        este se compone de 4 botones:
                -Buscar productos: que solicita un texto y busca los items que que contenga la linea de texto escrita.
                        mostrara una lista de los productos encontrados.

                -Eliminar producto: elimina los productos añadidos previamente al pedido.

                -Vaciar carrito: elimina todos los items del pedido.

                -Finalizar pedido: genera una vista previa del pedido(factura) y solicita una confirmacion final.
                        este pedido queda guardado en el excel.
    
    Ayuda: nos muestra un mensaje informativo acerca del funcionamiento del bot.
