# ---importar modulos---
import tkinter as tk
from tkinter import ttk
import subprocess
import funciones as fn
import env
import subprocess
import sys

# --- recursos ---
ico = env.ICO
textos = {
'mt_base': 'Bienvenido al lanzador de tu BOT .\n    *este le permitira: editar de manera rapida el contenido de su proyecto y manipular el estado del BOT.\n\n    -el boton "inventario" le permite vizualizar su inventario \n    (mediante doble click podra modificar los valores de cualquier casillas.)\n    (si desea recargar la pagina solo vuelva a presionarlo.)\n\n    -el boton "usuarios" le permite vizualizar su lista de usuarios \n    (mediante doble click podra modificar los valores de cualquier casillas.)\n    (si desea recargar la pagina solo vuelva a presionarlo.)\n\n    -el boton "pedidos" le permite vizualizar su lista de pedidos \n    (mediante doble click podra modificar los valores de cualquier casillas.)\n    (si desea recargar la pagina solo vuelva a presionarlo.)\n\n    -el boton "iniciar" permitira poner en linea el bot!\n    *tener claro que no debe existir ninguna instancia activa del mismo BOT*\n    *al inicial el BOT un boton verde en la parte inferior le confirmara que este esta en funcionamiento.\n\n    -el boton "finalizar" pemitira apagar el bot!\n    *tener en cuenta que cerrara la misma sesion que abrio el boton iniciar!\n    *es de importancia vital para el buen funcionamiento y constancia del bot \n    el apagarlo antes de realizar cualquier cambio en los archivos origen.\n    *al finalizar el BOT un boton rojo en la parte inferior le confirmara que este esta fuera de funcionamiento.\n\n*en pro de evitar posibles errores el BOT es dependiente de su lanzador, por lo tanto si cierra el lanzador:el BOT se detendra.'
}

bot_process = None


def crear_ventana_principal():
    # ---ventana principal---
    viewport = tk.Tk()
    # ---editar ventana---
    viewport.geometry('1280x480+100+100')
    viewport.config(bg='black')
    viewport.minsize(width=429, height=240)
    viewport.attributes(alpha=0.78)
    # viewport.overrideredirect(True)
    # --- icono
    try:
        icono = tk.PhotoImage(file=ico)
        viewport.iconphoto(False, icono)
    except tk.TclError as e:
        print(f'error {e} al cargar la imagen del icono')
    viewport.title('Lanzador del bot')
    return viewport


def cambiar_estado():
    global encendido
    if encendido:
        indicadorBot.config(text="Apagado", bg="red")
        encendido = False
    else:
        indicadorBot.config(text="Encendido", bg="green")
        encendido = True
encendido = False # variable global

def pedidos(event=None):
    print("Mostrando pedidos")
    fn.mostrar_pedidos(mt)  # Asegúrate de pasar el contenedor Frame 'mt'


def finalizar_bot_telegram(event: None):
    global bot_process
    if bot_process:
        print("Intentando finalizar el bot de Telegram...")
        bot_process.terminate()  # Envía una señal SIGTERM al proceso
        bot_process.wait(timeout=5)  # Espera hasta 5 segundos para que termine
        if bot_process.poll() is not None:
            print("El bot de Telegram ha finalizado.")
            cambiar_estado()
            bot_process = None
        else:
            print("El bot de Telegram no respondió a la señal SIGTERM, intentando matar el proceso...")
            bot_process.kill()  # Envía una señal SIGKILL (forzado)
            bot_process.wait()
            print("El bot de Telegram ha sido forzado a detenerse.")
            bot_process = None
    else:
        print("El bot de Telegram ha sido apagado")


def iniciar_bot_telegram(event: None):
    global bot_process
    python_executable_path = sys.executable  # Obtiene la ruta del intérprete actual

    if bot_process is None or bot_process.poll() is not None:
        try:
            bot_process = subprocess.Popen([python_executable_path, 'bot.py'])
            print("Bot de Telegram iniciado.")
            cambiar_estado()
        except FileNotFoundError:
            print("Error: El archivo 'bot.py' no se encontró.")
        except Exception as e:
            print(f"Error al iniciar el bot de Telegram: {e}")
    else:
        print("El bot de Telegram ya está en ejecución.")


def inventario(event=None):
    print(f'abriendo inventario')
    fn.mostrar_inventario(mt)  # ¡Pasa 'mt' como argumento!


def usuarios(event=None):
    print(f'mostrando usuarios')
    fn.mostrar_usuarios(mt)


def cerrar(event: None):
    print('cerrando app')
    finalizar_bot_telegram(event)
    viewport.destroy()


if __name__ == '__main__':
    viewport = crear_ventana_principal()

    # ---barra de navegacion---
    navbar = tk.Frame(viewport, bg='red')
    navbar.pack(side=tk.TOP, fill=tk.X)

    # ---botones navegacion ---

    btn_Inventario = tk.Button(navbar, text='Inventario', bg='black', fg='red', bd=8)
    btn_Inventario.pack(side=tk.LEFT)
    btn_Inventario.bind('<Button-1>', inventario)

    btn_usuarios = tk.Button(navbar, text='Usuarios', bg='black', fg='red', bd=8)
    btn_usuarios.pack(side=tk.LEFT)
    btn_usuarios.bind('<Button-1>', usuarios)

    btn_pedidos = tk.Button(navbar, text='pedidos', bg='black', fg='red', bd=8)
    btn_pedidos.pack(side=tk.LEFT)
    btn_pedidos.bind('<Button-1>', pedidos)

    btn_lanzarBot = tk.Button(navbar, text='Iniciar', bg='black', fg='red', bd=8)
    btn_lanzarBot.pack(side=tk.LEFT)
    btn_lanzarBot.bind('<Button-1>', iniciar_bot_telegram)

    btn_cerrarBot = tk.Button(navbar, text='finalizar', bg='black', fg='red', bd=8)
    btn_cerrarBot.pack(side=tk.LEFT)
    btn_cerrarBot.bind('<Button-1>', finalizar_bot_telegram)

    # ---cuerpo ---
    mt = tk.Frame(viewport)
    mt.pack(fill=tk.BOTH, expand=True)
    mt.config(bg='white')

    texto_mt = tk.Text(mt)
    texto_mt.pack(fill=tk.BOTH, expand=True)
    texto_mt.insert(tk.END, textos['mt_base'])  # Puedes agregar texto inicial aquí

    # --- pie de pagina ---

    pp = tk.Frame(viewport, bg='red')
    pp.pack(side=tk.BOTTOM, fill=tk.X)

    btn_Salida = tk.Button(pp, text='cerrar', bg='black', fg='red', bd=8)
    btn_Salida.pack(side=tk.RIGHT)
    btn_Salida.bind('<Button-1>', cerrar)
    
    indicadorBot = tk.Button(pp, text='Apagado', bg='red', bd=8)
    indicadorBot.pack(side=tk.LEFT)
    indicadorBot.bind('<Button-1>', cambiar_estado)

    viewport.protocol("WM_DELETE_WINDOW", lambda: finalizar_bot_telegram(None) or viewport.destroy())
    # ---poner la venatana en loop---
    tk.mainloop()
    # ---fin...