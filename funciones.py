#--- MODULOS ---
import tkinter as tk
from tkinter import ttk, simpledialog
import openpyxl
from tkinter import messagebox
import env
import pandas as pd
import bot
import os
import arrow

#--- RECURSOS ---
archivo_inventario = env.EXCEL


#--- FUNCIONES ---
def mostrar_pedidos(contenedor_mt):
    """Función para mostrar los datos de pedidos en el contenedor Frame."""
    for widget in contenedor_mt.winfo_children():
        widget.destroy()

    pedidos_df = cargar_pedidos()

    if pedidos_df.empty:
        return

    columnas = list(pedidos_df.columns)
    tree = ttk.Treeview(contenedor_mt, columns=columnas, show='headings')

    for columna in columnas:
        tree.heading(columna, text=columna)
        tree.column(columna, width=100)  # Ancho inicial de las columnas

    for index, row in pedidos_df.iterrows():
        tree.insert('', tk.END, values=list(row))

    #  # Añadir el evento de doble clic para editar celdas de pedidos
    tree.bind("<Double-1>", lambda event: editar_celda(event, tree, "pedidos"))

    tree.pack(fill=tk.BOTH, expand=True)

def cargar_pedidos():
    """Función para leer los datos de pedidos desde la hoja 'Pedidos'."""
    try:
        pedidos = pd.read_excel(archivo_inventario, sheet_name='Pedidos')
        return pedidos
    except FileNotFoundError:
        print(f"Error: El archivo '{archivo_inventario}' no fue encontrado.")
        return pd.DataFrame()
    except KeyError:
        print(f"Error: La hoja 'Pedidos' no fue encontrada en el archivo '{archivo_inventario}'.")
        return pd.DataFrame()
    except Exception as e:
        print(f"Error al cargar pedidos: {e}")
        return pd.DataFrame()

def obtener_datos_usuario(chat_id):
    """Obtiene los datos completos de un usuario por su ID de Telegram."""
    try:
        usuarios = pd.read_excel(archivo_inventario, sheet_name='Hoja 3')
        usuario = usuarios[usuarios['ID_TELEGRAM'] == chat_id]
        if not usuario.empty:
            return usuario.iloc[0].to_dict()
        return None
    except Exception as e:
        print(f"Error al obtener datos de usuario: {e}")
        return None


def obtener_info_producto(ref):
    """Obtiene la información de un producto por su referencia."""
    try:
        inventario = cargar_inventario()
        producto = inventario[inventario['REF'] == ref]
        if not producto.empty:
            return {
                'ref': ref,
                'descripcion': producto['DESCRIPCION'].iloc[0],
                'precio': float(producto['PRECIO_DE_VENTA_UNITARIO'].iloc[0]),
                'stock': int(producto['CONTROL_INVENTARIO'].iloc[0])
            }
        return None
    except Exception as e:
        print(f"Error al obtener información del producto: {e}")
        return None


def guardar_pedido(chat_id, num_pedido, items_carrito):
    """
    Guarda un pedido en la hoja de pedidos del Excel.
    
    Args:
        chat_id: ID de Telegram del cliente
        num_pedido: Número único de pedido
        items_carrito: Lista de productos en el carrito
        
    Returns:
        bool: True si se guardó correctamente, False en caso contrario
    """
    try:
        print(f"Iniciando guardar_pedido para chat_id: {chat_id}, num_pedido: {num_pedido}")  # Debug

        # Obtener datos del usuario
        datos_usuario = obtener_datos_usuario(chat_id)
        if not datos_usuario:
            print(f"Error: No se pudieron obtener datos del usuario para chat_id: {chat_id}")  # Debug
            return False
        print(f"Datos del usuario obtenidos: {datos_usuario}")  # Debug
        
        # Obtener fecha actual
        fecha_actual = arrow.now().strftime("%d/%m/%Y %H:%M")
        
        # Crear DataFrame para los pedidos
        pedidos_data = []
        
        for item in items_carrito:
            pedidos_data.append({
                'NUM_PEDIDO': num_pedido,
                'FECHA': fecha_actual,
                'ID_TELEGRAM': chat_id,
                'NOMBRE_CLIENTE': datos_usuario['NOMBRE'],
                'TELEFONO': datos_usuario['TELEFONO'],
                'CORREO': datos_usuario['CORREO'],
                'DIRECCION': datos_usuario['DIRECCION'],
                'REF_PRODUCTO': item['ref'],
                'DESCRIPCION': item['descripcion'],
                'CANTIDAD': item['cantidad'],
                'PRECIO_UNITARIO': item['precio'],
                'TOTAL_ITEM': item['cantidad'] * item['precio'],
                'ESTADO': 'PENDIENTE'
            })
        
        df_pedidos = pd.DataFrame(pedidos_data)
        
        # Verificar si existe la hoja de pedidos
        try:
            # Intentar leer la hoja existente
            pedidos_existentes = pd.read_excel(archivo_inventario, sheet_name='Pedidos')
            # Concatenar con los nuevos pedidos
            df_actualizada = pd.concat([pedidos_existentes, df_pedidos], ignore_index=True)
        except:
            # Si no existe, usar solo los nuevos pedidos
            df_actualizada = df_pedidos
        
        # Guardar en Excel
        with pd.ExcelWriter(archivo_inventario, engine='openpyxl', mode='a', if_sheet_exists='replace') as writer:
            df_actualizada.to_excel(writer, sheet_name='Pedidos', index=False)
        
        # Actualizar inventario (restar stock)
        for item in items_carrito:
            # Obtener stock actual
            info_producto = obtener_info_producto(item['ref'])
            if info_producto:
                nuevo_stock = info_producto['stock'] - item['cantidad']
                if nuevo_stock < 0:
                    nuevo_stock = 0
                # Actualizar stock
                guardar_cambio_inventario(item['ref'], 'CONTROL_INVENTARIO', nuevo_stock)
        print("Pedido guardado exitosamente.")  # Debug
        return True
    except Exception as e:
        print(f"Error al guardar pedido: {e}")  # Debug
        return False

def quitar_tildes_manual(texto):
    texto = str(texto)
    replacements = {
        'á': 'a', 'é': 'e', 'í': 'i', 'ó': 'o', 'ú': 'u',
        'Á': 'A', 'É': 'E', 'Í': 'I', 'Ó': 'O', 'Ú': 'U'
    }
    for a, b in replacements.items():
        texto = texto.replace(a, b)
    return texto.upper()

#consulta descripcion
def buscar_producto(consulta):
    print(f"Iniciando búsqueda de: {consulta}")
    try:
        inventario = cargar_inventario()
        print(f"Inventario cargado: {len(inventario)} registros")
        
        # Limpiar y preparar la consulta
        consulta = quitar_tildes_manual(str(consulta)).lower()
        print(f"Consulta limpia: {consulta}")
        
        # Convertir columnas a string y aplicar limpieza
        inventario['REF_LIMPIA'] = inventario['REF'].astype(str).apply(lambda x: quitar_tildes_manual(x).lower())
        inventario['DESC_LIMPIA'] = inventario['DESCRIPCION'].astype(str).apply(lambda x: quitar_tildes_manual(x).lower())
        
        # Crear máscaras para diferentes tipos de búsqueda
        ref_exacta = inventario['REF_LIMPIA'].str.contains(consulta, case=False, na=False)
        ref_comienza = inventario['REF_LIMPIA'].str.startswith(consulta, na=False)
        desc_contiene = inventario['DESC_LIMPIA'].str.contains(consulta, case=False, na=False)
        
        # Búsqueda por palabras parciales si no hay resultados exactos
        mask = ref_exacta | ref_comienza | desc_contiene
        
        if not mask.any():
            # Si no hay resultados, intentar búsqueda más flexible
            palabras = consulta.split()
            for palabra in palabras:
                if len(palabra) >= 2:  # Solo para palabras de 2 o más caracteres
                    palabra_mask = (
                        inventario['REF_LIMPIA'].str.contains(palabra, case=False, na=False) |
                        inventario['DESC_LIMPIA'].str.contains(palabra, case=False, na=False)
                    )
                    mask = mask | palabra_mask
        
        resultados = inventario[mask].drop(['REF_LIMPIA', 'DESC_LIMPIA'], axis=1)
        print(f"Resultados encontrados: {len(resultados)}")
        
        return resultados
        
    except Exception as e:
        print(f"Error en búsqueda: {e}")
        return pd.DataFrame()

def guardar_usuario(chat_id, nombre, telefono, correo, direccion):
    if not all([nombre.strip(), telefono.strip(), correo.strip(), direccion.strip()]):
        bot.BOT.send_message(chat_id, "Todos los campos son obligatorios y no pueden estar vacíos.")
        return False

    try:
        nuevo_usuario = pd.DataFrame({
            'ID_TELEGRAM': [chat_id],
            'NOMBRE': [nombre.strip()],
            'TELEFONO': [telefono.strip()],
            'CORREO': [correo.strip()],
            'DIRECCION': [direccion.strip()],
            'TIPO': [1]  # tipo por defecto
        })

        try:
            if os.path.exists(archivo_inventario):
                df_existente = pd.read_excel(archivo_inventario, sheet_name='Hoja 3')

                if chat_id in df_existente['ID_TELEGRAM'].values:
                    bot.BOT.send_message(chat_id, "Ya estás registrado en el sistema.")
                    return False

                df_actualizado = pd.concat([df_existente, nuevo_usuario], ignore_index=True)

                with pd.ExcelWriter(archivo_inventario, engine='openpyxl', mode='a', if_sheet_exists='replace') as writer:
                    df_actualizado.to_excel(writer, sheet_name='Hoja 3', index=False)

                bot.BOT.send_message(chat_id, "¡Registro completado!")
                return True

            else:
                bot.BOT.send_message(chat_id, "Error: El archivo de registro no existe.")
                return False

        except Exception as e:
            print(f"Error al escribir en Excel: {e}")
            bot.BOT.send_message(chat_id, "Error al guardar el registro. Por favor, intente nuevamente.")
            return False

    except Exception as e:
        print(f"Error en guardar_usuario: {e}")
        bot.BOT.send_message(chat_id, "Ocurrió un error al guardar el usuario.")
        return False


def usuario_registrado(chat_id):
    try:
        usuarios = pd.read_excel(archivo_inventario, sheet_name='Hoja 3')
        return chat_id in usuarios['ID_TELEGRAM'].values
    except Exception as e:
        print(f"Error al verificar usuario registrado: {e}")
        return False


def obtener_tipo_usuario(telegram_id):
    """
    Obtiene el tipo de usuario desde el archivo Excel basado en el ID de Telegram.
    Args:
        telegram_id (int): El ID de Telegram del usuario a buscar.
    Returns:
        str or None: El tipo de usuario si se encuentra, None si no.
    """
    usuarios_df = cargar_usuarios()
    if not usuarios_df.empty:
        # Asegúrate de que la columna 'ID_TELEGRAM' exista y busca la coincidencia
        if 'ID_TELEGRAM' in usuarios_df.columns:
            usuario_data = usuarios_df[usuarios_df['ID_TELEGRAM'] == telegram_id]
            if not usuario_data.empty:
                # Asegúrate de que la columna 'TIPO_USUARIO' exista
                if 'TIPO' in usuario_data.columns:
                    return int(usuario_data['TIPO'].iloc[0])
                else:
                    print("Error: La columna 'TIPO' no se encuentra en el archivo de usuarios.")
                    return None
            else:
                return None  # Usuario no encontrado
        else:
            print("Error: La columna 'ID_TELEGRAM' no se encuentra en el archivo de usuarios.")
            return None
    else:
        return None  # No se pudieron cargar los usuarios


def cargar_inventario():
    """Función para leer y procesar los datos del inventario desde un archivo XLSX usando pandas."""
    try:
        inventario = pd.read_excel(archivo_inventario, sheet_name='Hoja 1')  # hoja inventario
        # Convertimos a numérico el valor de las columnas de precios y stock
        inventario['PRECIO_DE_VENTA_UNITARIO'] = pd.to_numeric(inventario['PRECIO_DE_VENTA_UNITARIO'], errors='coerce')
        inventario['CONTROL_INVENTARIO'] = pd.to_numeric(inventario['CONTROL_INVENTARIO'], errors='coerce')
        # Borramos contenido con valores nulos en columnas importantes
        inventario.dropna(subset=['DESCRIPCION', 'REF', 'CONTROL_INVENTARIO', 'PRECIO_DE_VENTA_UNITARIO'], inplace=True)
        return inventario
    except FileNotFoundError:
        print(f"Error: El archivo '{archivo_inventario}' no fue encontrado.")
        return pd.DataFrame()
    except KeyError:
        print(f"Error: La hoja 'Hoja 1' no fue encontrada en el archivo '{archivo_inventario}'.")
        return pd.DataFrame()
    except Exception as e:
        print(f"Error al cargar inventario con pandas: {e}")
        return pd.DataFrame()


def cargar_usuarios():
    """Función para leer los datos de usuarios desde la hoja 'Hoja 3' de un archivo XLSX usando pandas."""
    try:
        usuarios = pd.read_excel(archivo_inventario, sheet_name='Hoja 3')  # hoja registro de usuarios
        return usuarios
    except FileNotFoundError:
        print(f"Error: El archivo '{archivo_inventario}' no fue encontrado.")
        return pd.DataFrame()
    except KeyError:
        print(f"Error: La hoja 'Hoja 3' no fue encontrada en el archivo '{archivo_inventario}'.")
        return pd.DataFrame()
    except Exception as e:
        print(f"Error al cargar usuarios con pandas: {e}")
        return pd.DataFrame()


def guardar_cambio_inventario(item_id, columna, nuevo_valor):
    """Guarda el cambio en el archivo Excel."""
    try:
        # Cargar el libro de trabajo
        libro = openpyxl.load_workbook(archivo_inventario)
        hoja = libro['Hoja 1']

        # Obtener los encabezados
        encabezados = [celda.value for celda in hoja[1]]

        # Encontrar la columna a actualizar
        columna_a_actualizar = None
        for i, encabezado in enumerate(encabezados):
            if encabezado == columna:
                columna_a_actualizar = i
                break

        # Verificar si encontramos la columna
        if columna_a_actualizar is None:
            print(f"Error: No se encontró la columna {columna}")
            return False

        # En inventario (Hoja 1), usaremos la primera columna como identificador
        columna_id = 0

        # Buscamos la fila que contiene el item_id
        fila_a_actualizar = None
        for i, fila in enumerate(hoja.iter_rows(min_row=2, values_only=True), start=2):
            if str(fila[columna_id]) == str(item_id):
                fila_a_actualizar = i
                break

        # Si encontramos la fila, actualizamos el valor
        if fila_a_actualizar:
            # Convertimos el índice de columna a letra (A, B, C, etc.)
            letra_columna = openpyxl.utils.get_column_letter(columna_a_actualizar + 1)
            celda = f"{letra_columna}{fila_a_actualizar}"

            # Actualizamos el valor
            hoja[celda] = nuevo_valor

            # Guardamos los cambios
            libro.save(archivo_inventario)
            return True
        else:
            print(f"Error: No se encontró el item con ID {item_id}")
            return False

    except Exception as e:
        print(f"Error al guardar cambios: {e}")
        return False

def guardar_cambio_pedidos(num_pedido, columna, nuevo_valor):
    """Guarda el cambio en el archivo Excel para la hoja de pedidos."""
    try:
        libro = openpyxl.load_workbook(archivo_inventario)
        hoja = libro['Pedidos']

        encabezados = [celda.value for celda in hoja[1]]

        columna_a_actualizar = None
        for i, encabezado in enumerate(encabezados):
            if encabezado.strip().upper() == columna.strip().upper():
                columna_a_actualizar = i
                break

        if columna_a_actualizar is None:
            print(f"Error: No se encontró la columna {columna}")
            return False

        # En pedidos (Hoja 'Pedidos'), la primera columna es NUM_PEDIDO
        columna_id = 0

        fila_a_actualizar = None
        for i, fila in enumerate(hoja.iter_rows(min_row=2, values_only=True), start=2):
            excel_id_str = str(fila[columna_id]).strip()
            num_pedido_str = str(num_pedido).strip()

            if excel_id_str == num_pedido_str:
                fila_a_actualizar = i
                break

        if fila_a_actualizar:
            letra_columna = openpyxl.utils.get_column_letter(columna_a_actualizar + 1)
            celda = f"{letra_columna}{fila_a_actualizar}"
            hoja[celda] = nuevo_valor
            libro.save(archivo_inventario)
            return True
        else:
            print(f"Error: No se encontró el pedido con NUM_PEDIDO {num_pedido}")
            return False

    except Exception as e:
        print(f"Error al guardar cambios en pedidos: {e}")
        return False

def guardar_cambio_usuarios(item_id, columna, nuevo_valor):
    """Guarda el cambio en el archivo Excel para la hoja de usuarios."""
    try:
        # Cargar el libro de trabajo
        libro = openpyxl.load_workbook(archivo_inventario)
        hoja = libro['Hoja 3']

        # Obtener los encabezados
        encabezados = [celda.value for celda in hoja[1]]

        # Encontrar la columna a actualizar
        columna_a_actualizar = None
        for i, encabezado in enumerate(encabezados):
            if encabezado.strip().upper() == columna.strip().upper():
                columna_a_actualizar = i
                break

        if columna_a_actualizar is None:
            print(f"Error: No se encontró la columna {columna}")
            return False

        # En usuarios (Hoja 3), la primera columna es ID_TELEGRAM
        columna_id = 0

        # Buscamos la fila que contiene el item_id
        fila_a_actualizar = None
        for i, fila in enumerate(hoja.iter_rows(min_row=2, values_only=True), start=2):
            # Convertimos ambos IDs a string y tomamos la parte entera para comparar
            excel_id_str = str(fila[columna_id]).split('.')[0] if isinstance(fila[columna_id], (int, float)) else str(
                fila[columna_id])
            item_id_str = str(item_id).split('.')[0] if isinstance(item_id, (int, float)) else str(item_id)

            print(f"Comparando ID (convertidos): '{excel_id_str}' con '{item_id_str}'")  # Debugging
            if excel_id_str == item_id_str:
                fila_a_actualizar = i
                break

        if fila_a_actualizar:
            letra_columna = openpyxl.utils.get_column_letter(columna_a_actualizar + 1)
            celda = f"{letra_columna}{fila_a_actualizar}"
            hoja[celda] = nuevo_valor
            libro.save(archivo_inventario)
            return True
        else:
            print(f"Error: No se encontró el usuario con ID {item_id}")
            return False

    except Exception as e:
        print(f"Error al guardar cambios: {e}")
        return False


def mostrar_inventario(contenedor_mt):
    """Función para mostrar los datos del inventario desde un DataFrame en el contenedor Frame."""
    for widget in contenedor_mt.winfo_children():
        widget.destroy()

    inventario_df = cargar_inventario()  # Ahora 'inventario' es un DataFrame

    if inventario_df.empty:
        return

    columnas = list(inventario_df.columns)
    tree = ttk.Treeview(contenedor_mt, columns=columnas, show='headings')

    for columna in columnas:
        tree.heading(columna, text=columna)
        tree.column(columna, width=100)

    for index, row in inventario_df.iterrows():
        tree.insert('', tk.END, values=list(row))  # Insertamos la fila como una lista

    # Añadir el evento de doble clic (asumiendo que 'editar_celda' está definida)
    tree.bind("<Double-1>", lambda event: editar_celda(event, tree, "inventario"))

    tree.pack(fill=tk.BOTH, expand=True)


def mostrar_usuarios(contenedor_mt):
    """Función para mostrar los datos de usuarios desde un DataFrame en el contenedor Frame."""
    for widget in contenedor_mt.winfo_children():
        widget.destroy()

    usuarios_df = cargar_usuarios()  # Ahora 'usuarios' es un DataFrame

    print("Contenido del DataFrame usuarios_df:")  # Debugging
    print(usuarios_df)  # Debugging

    if usuarios_df.empty:
        return

    columnas = list(usuarios_df.columns)
    tree = ttk.Treeview(contenedor_mt, columns=columnas, show='headings')

    for columna in columnas:
        tree.heading(columna, text=columna)
        tree.column(columna, width=100)

    for index, row in usuarios_df.iterrows():
        tree.insert('', tk.END, values=list(row))  # Insertamos la fila como una lista

    # Añadir el evento de doble clic (asumiendo que 'editar_celda' está definida)
    tree.bind("<Double-1>", lambda event: editar_celda(event, tree, "usuarios"))

    tree.pack(fill=tk.BOTH, expand=True)


# Asumiendo que tienes una función cargar_usuarios() que devuelve un DataFrame
def cargar_usuarios():
    try:
        return pd.read_excel(archivo_inventario, sheet_name='Hoja 3')
    except Exception as e:
        print(f"Error al cargar usuarios: {e}")
        return pd.DataFrame()


def editar_celda(event, tree, tipo_datos):
    """Función para editar el valor de una celda con doble clic."""
    # Obtener el elemento seleccionado
    item = tree.identify('item', event.x, event.y)
    print(f"Elemento seleccionado (item): {item}")  # Debugging

    if not item:
        return

    # Obtener la columna seleccionada
    columna_index = tree.identify_column(event.x)
    columna_num = int(columna_index.replace('#', '')) - 1

    # Obtener el nombre de la columna
    columnas = tree['columns']
    if columna_num >= len(columnas):
        return
    columna_nombre = columnas[columna_num]

    # Obtener el valor actual
    valores = tree.item(item, 'values')
    print(f"Valores de la fila seleccionada: {valores}")  # Debugging
    if valores:  # Asegurarse de que la lista de valores no esté vacía
        item_id = valores[0]
        print(f"ID del elemento (desde valores[0]): {item_id}")  # Debugging

        # Crear ventana de edición
        ventana_edicion = tk.Toplevel()
        ventana_edicion.title(f"Editar {columna_nombre}")
        ventana_edicion.geometry("300x150")
        ventana_edicion.resizable(False, False)

        # Centrar ventana
        ventana_edicion.geometry("+%d+%d" % (
            ventana_edicion.winfo_screenwidth() // 2 - 150,
            ventana_edicion.winfo_screenheight() // 2 - 75
        ))

        # Etiqueta con el valor actual
        tk.Label(ventana_edicion, text=f"Valor actual:").pack(pady=(10, 0))
        tk.Label(ventana_edicion, text=str(valores[columna_num] if columna_num < len(valores) else "")).pack()

        # Entrada para el nuevo valor
        tk.Label(ventana_edicion, text="Nuevo valor:").pack(pady=(10, 0))
        entrada = tk.Entry(ventana_edicion, width=30)
        entrada.pack(pady=(0, 10))
        entrada.insert(0, str(valores[columna_num] if columna_num < len(valores) else ""))
        entrada.select_range(0, tk.END)
        entrada.focus_set()

        # Función para guardar el cambio
        def guardar():
            nuevo_valor = entrada.get()

            # Imprimir información de depuración
            print(f"ID del elemento: {item_id}")
            print(f"Columna: {columna_nombre}")
            print(f"Nuevo valor: {nuevo_valor}")
            print(f"Tipo de datos: {tipo_datos}")

            # Guardar en Excel según tipo de datos
            exito = False
            if tipo_datos == "inventario":
                exito = guardar_cambio_inventario(item_id, columna_nombre, nuevo_valor)
            elif tipo_datos == "usuarios":
                exito = guardar_cambio_usuarios(item_id, columna_nombre, nuevo_valor)
            elif tipo_datos == "pedidos":
                exito = guardar_cambio_pedidos(valores[0], columna_nombre, nuevo_valor) # Pasar el num_pedido

            if exito:
                # Actualizar el valor en el árbol
                nuevos_valores = list(valores)
                nuevos_valores[columna_num] = nuevo_valor
                tree.item(item, values=nuevos_valores)
                messagebox.showinfo("Éxito", "Valor actualizado correctamente")
            else:
                messagebox.showerror("Error", "No se pudo actualizar el valor")

            ventana_edicion.destroy()

        # Botón para confirmar
        boton_guardar = tk.Button(ventana_edicion, text="Guardar", command=guardar)
        boton_guardar.pack(pady=10)

        ventana_edicion.transient()
        ventana_edicion.grab_set()
        ventana_edicion.focus_set()
        ventana_edicion.wait_window()