#---modulo---
import telebot as tb
from telebot import types
import env
import funciones as fn
import os
import pandas as pd
import arrow
import logging
 

#---recursos---
TOKEN = env.TOKEN
user_registration_state = {}
user_data = {}
IMAGENES_PATH = env.IMG  # Ruta a la carpeta de imágenes

# --- Variables Globales ---
resultados_busqueda = {}  # Para almacenar los DataFrames de resultados
pagina_actual = {}  # Para almacenar la página actual por chat_id


# Configurar logging (asegúrate de hacerlo al inicio del archivo)
logging.basicConfig(filename='bot_errors.log', level=logging.ERROR,
                    format='%(asctime)s - %(levelname)s - %(message)s')


#---conexion al bot---
BOT = tb.TeleBot(TOKEN)

# Estados para el proceso de pedido
pedido_state = {}  # Almacena el estado del pedido para cada usuario
carrito = {}  # Almacena los productos en el carrito de cada usuario


#--- saludo---

@BOT.message_handler(commands=['start'])
def comando_start(message):
    chat_id = message.chat.id
    
    # Ruta a la imagen que deseas enviar
    imagen_path = env.ICO  # **CAMBIA ESTO**
    
    # Texto que acompañará a la imagen
    texto_saludo = (
        "👋 ¡Hola! Bienvenido a nuestro bot.\n"
        "Aquí puedes explorar nuestro catálogo, realizar pedidos y mucho más.\n"
    )
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)  # Usar ReplyKeyboardMarkup para botones en el chat
    
    btn_pedido = types.KeyboardButton('🛒 Pedido')
    btn_ayuda = types.KeyboardButton('❓ Ayuda')
    markup.add(btn_pedido, btn_ayuda)
    
    # Verificar si el usuario está registrado
    if not fn.usuario_registrado(chat_id):
        btn_registrar = types.KeyboardButton('📝 Registrarse')
        markup.add(btn_registrar)
        texto_saludo += "\n¡Parece que aún no estás registrado! Usa el botón 'Registrarse' para crear tu cuenta y acceder a todas las funciones."
    else:
        texto_saludo += "\n¡Ya estás registrado! Usa los botones de abajo para navegar."
    
    try:
        # Enviar la imagen
        with open(imagen_path, 'rb') as photo:
            BOT.send_photo(chat_id, photo, caption=texto_saludo, reply_markup=markup)
    except FileNotFoundError:
        # Si la imagen no se encuentra, enviar solo el texto
        BOT.send_message(chat_id, texto_saludo, reply_markup=markup)
        print(f"Error: No se encontró la imagen en la ruta: {imagen_path}")
    except Exception as e:
        # Si ocurre otro error, registrarlo
        print(f"Error al enviar el mensaje de inicio: {e}")
        BOT.send_message(chat_id, texto_saludo, reply_markup=markup) # Enviar el texto como respaldo

#--- Manejadores de los botones ---

@BOT.message_handler(func=lambda message: message.text == '🛒 Pedido')
def handle_pedido_button(message):
    BOT.send_message(message.chat.id, "Iniciando proceso de pedido...", reply_markup=types.ReplyKeyboardRemove())
    iniciar_pedido(message)  # Llama directamente a la función de pedido

@BOT.message_handler(func=lambda message: message.text == '📝 Registrarse')
def handle_registrar_button(message):
    chat_id = message.chat.id
    BOT.send_message(chat_id, "Iniciando registro...", reply_markup=types.ReplyKeyboardRemove())
    iniciar_registro(message)  # Llama a la función de registro
    # Si quieres simular el comando /registrar (menos recomendado):
    # BOT.process_new_messages([types.Message(message.message_id + 1, message.from_user, message.date, message.chat, 'text', '/registrar')])

@BOT.message_handler(func=lambda message: message.text == '❓ Ayuda')
def handle_ayuda_button(message):
    BOT.send_message(message.chat.id, "Mostrando ayuda...", reply_markup=types.ReplyKeyboardRemove())
    comando_ayuda(message)

        
#---pedidos---
@BOT.message_handler(commands=['pedido'])
def iniciar_pedido(message):
    chat_id = message.chat.id
    
    # Verificar si el usuario está registrado
    if not fn.usuario_registrado(chat_id):
        BOT.send_message(chat_id, "❌ Debes estar registrado para realizar pedidos. Usa /registrar para crear una cuenta.")
        return
    
    # Inicializar el carrito del usuario si no existe
    if chat_id not in carrito:
        carrito[chat_id] = []
    
    # Mostrar opciones de pedido
    markup = types.InlineKeyboardMarkup(row_width=2)
    
    btn_buscar = types.InlineKeyboardButton("🔍 Buscar productos", callback_data='pedido_buscar')
    btn_ver_carrito = types.InlineKeyboardButton("🛒 Ver carrito", callback_data='ver_carrito')
    btn_finalizar = types.InlineKeyboardButton("✅ Finalizar pedido", callback_data='finalizar_pedido')
    btn_cancelar = types.InlineKeyboardButton("❌ Cancelar pedido", callback_data='cancelar_pedido')
    
    markup.add(btn_buscar, btn_ver_carrito)
    markup.add(btn_finalizar, btn_cancelar)
    
    # Mensaje con conteo de items si hay productos en el carrito
    if chat_id in carrito and carrito[chat_id]:
        total_items = sum(item['cantidad'] for item in carrito[chat_id])
        total_precio = sum(item['precio'] * item['cantidad'] for item in carrito[chat_id])
        mensaje = (f"🛍️ *TU PEDIDO ACTUAL*\n\n"
                  f"📦 Items en carrito: {total_items}\n"
                  f"💰 Total: ${total_precio:,.2f}\n\n"
                  f"¿Qué deseas hacer?")
    else:
        mensaje = "🛍️ *NUEVO PEDIDO*\n\nTu carrito está vacío. ¿Qué deseas hacer?"
    
    BOT.send_message(chat_id, mensaje, reply_markup=markup, parse_mode="Markdown")


@BOT.callback_query_handler(func=lambda call: call.data == 'pedido_buscar')
def pedir_termino_busqueda(call):
    chat_id = call.message.chat.id
    
    # Establecer estado para capturar la búsqueda
    pedido_state[chat_id] = 'esperando_termino_busqueda'
    
    BOT.send_message(chat_id, "🔍 Por favor, escribe el nombre o referencia del producto que buscas:")
    BOT.answer_callback_query(call.id)


@BOT.callback_query_handler(func=lambda call: call.data == 'ver_carrito')
def mostrar_carrito(call):
    chat_id = call.message.chat.id
    
    if chat_id not in carrito or not carrito[chat_id]:
        BOT.send_message(chat_id, "🛒 Tu carrito está vacío.")
        BOT.answer_callback_query(call.id)
        return
    
    # Mostrar los productos en el carrito
    mensaje = "🛒 *CONTENIDO DE TU CARRITO*\n\n"
    
    total_pedido = 0
    for i, item in enumerate(carrito[chat_id], 1):
        subtotal = item['precio'] * item['cantidad']
        total_pedido += subtotal
        
        mensaje += (f"*{i}. {item['descripcion']}*\n"
                   f"   📌 Ref: `{item['ref']}`\n"
                   f"   📦 Cantidad: {item['cantidad']}\n"
                   f"   💲 Precio unit: ${item['precio']:,.2f}\n"
                   f"   💰 Subtotal: ${subtotal:,.2f}\n\n")
    
    mensaje += f"*TOTAL DEL PEDIDO: ${total_pedido:,.2f}*\n\n"
    mensaje += "Para modificar tu pedido usa los botones de abajo 👇"
    
    # Opciones para gestionar el carrito
    markup = types.InlineKeyboardMarkup(row_width=2)
    btn_seguir = types.InlineKeyboardButton("➕ Añadir más", callback_data='pedido_buscar')
    btn_finalizar = types.InlineKeyboardButton("✅ Finalizar pedido", callback_data='finalizar_pedido')
    btn_vaciar = types.InlineKeyboardButton("🗑️ Vaciar carrito", callback_data='vaciar_carrito')
    btn_eliminar = types.InlineKeyboardButton("❌ Eliminar producto", callback_data='eliminar_producto')
    
    markup.add(btn_seguir, btn_finalizar)
    markup.add(btn_eliminar, btn_vaciar)
    
    BOT.send_message(chat_id, mensaje, reply_markup=markup, parse_mode="Markdown")
    BOT.answer_callback_query(call.id)


@BOT.callback_query_handler(func=lambda call: call.data == 'vaciar_carrito')
def vaciar_carrito_callback(call):
    chat_id = call.message.chat.id
    
    if chat_id in carrito:
        carrito[chat_id] = []
        BOT.send_message(chat_id, "🗑️ Has vaciado tu carrito.")
    
    # Mostrar nuevamente el menú de pedido
    iniciar_pedido(call.message)
    BOT.answer_callback_query(call.id)


@BOT.callback_query_handler(func=lambda call: call.data == 'eliminar_producto')
def pedir_producto_eliminar(call):
    chat_id = call.message.chat.id
    
    if chat_id not in carrito or not carrito[chat_id]:
        BOT.send_message(chat_id, "🛒 Tu carrito está vacío.")
        BOT.answer_callback_query(call.id)
        return
    
    # Crear lista de productos para seleccionar
    markup = types.InlineKeyboardMarkup(row_width=1)
    
    for i, item in enumerate(carrito[chat_id], 1):
        btn_text = f"{i}. {item['descripcion']} ({item['cantidad']} x ${item['precio']:,.2f})"
        markup.add(types.InlineKeyboardButton(btn_text, callback_data=f'eliminar_{i-1}'))
    
    markup.add(types.InlineKeyboardButton("🔙 Volver", callback_data='ver_carrito'))
    
    BOT.send_message(chat_id, "❌ Selecciona el producto que deseas eliminar:", reply_markup=markup)
    BOT.answer_callback_query(call.id)


@BOT.callback_query_handler(func=lambda call: call.data.startswith('eliminar_'))
def eliminar_producto_carrito(call):
    chat_id = call.message.chat.id
    
    try:
        # Extraer el índice del producto a eliminar
        indice = int(call.data.split('_')[1])
        
        if chat_id in carrito and 0 <= indice < len(carrito[chat_id]):
            producto_eliminado = carrito[chat_id].pop(indice)
            BOT.send_message(
                chat_id, 
                f"✅ Producto eliminado: *{producto_eliminado['descripcion']}*", 
                parse_mode="Markdown"
            )
        
        # Mostrar el carrito actualizado
        mostrar_carrito(call)
    except Exception as e:
        print(f"Error al eliminar producto: {e}")
        BOT.send_message(chat_id, "❌ Ocurrió un error al eliminar el producto.")
    
    BOT.answer_callback_query(call.id)


@BOT.callback_query_handler(func=lambda call: call.data == 'finalizar_pedido')
def finalizar_pedido(call):
    chat_id = call.message.chat.id
    
    if chat_id not in carrito or not carrito[chat_id]:
        BOT.send_message(chat_id, "❌ No puedes finalizar un pedido con el carrito vacío.")
        BOT.answer_callback_query(call.id)
        return
    
    # Obtener datos del usuario
    datos_usuario = fn.obtener_datos_usuario(chat_id)
    
    if not datos_usuario:
        BOT.send_message(chat_id, "❌ No se pudieron obtener tus datos. Por favor, contacta al administrador.")
        BOT.answer_callback_query(call.id)
        return
    
    # Confirmar el pedido
    mensaje = "✅ *CONFIRMACIÓN DE PEDIDO*\n\n"
    mensaje += f"👤 *Cliente:* {datos_usuario['NOMBRE']}\n"
    mensaje += f"📱 *Teléfono:* {datos_usuario['TELEFONO']}\n"
    mensaje += f"📧 *Email:* {datos_usuario['CORREO']}\n"
    mensaje += f"🏠 *Dirección:* {datos_usuario['DIRECCION']}\n\n"
    
    mensaje += "🛍️ *PRODUCTOS:*\n\n"
    
    total_pedido = 0
    for i, item in enumerate(carrito[chat_id], 1):
        subtotal = item['precio'] * item['cantidad']
        total_pedido += subtotal
        
        mensaje += (f"{i}. {item['descripcion']}\n"
                   f"   Ref: {item['ref']} - Cant: {item['cantidad']} x ${item['precio']:,.2f} = ${subtotal:,.2f}\n")
    
    mensaje += f"\n*TOTAL: ${total_pedido:,.2f}*\n\n"
    mensaje += "¿Confirmas este pedido?"
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    btn_confirmar = types.InlineKeyboardButton("✅ Confirmar", callback_data='confirmar_pedido_final')
    btn_cancelar = types.InlineKeyboardButton("❌ Cancelar", callback_data='cancelar_pedido')
    
    markup.add(btn_confirmar, btn_cancelar)
    
    BOT.send_message(chat_id, mensaje, reply_markup=markup, parse_mode="Markdown")
    BOT.answer_callback_query(call.id)


@BOT.callback_query_handler(func=lambda call: call.data == 'confirmar_pedido_final')
def guardar_pedido_final(call):
    chat_id = call.message.chat.id
    
    if chat_id not in carrito or not carrito[chat_id]:
        BOT.send_message(chat_id, "❌ No hay productos en el carrito.")
        BOT.answer_callback_query(call.id)
        return
    
    # Generar número de pedido único (fecha + últimos dígitos del chat_id)
    fecha_actual = arrow.now().format("YYYYMMDD")
    id_corto = str(chat_id)[-4:] if len(str(chat_id)) > 4 else str(chat_id)
    num_pedido = f"P{fecha_actual}{id_corto}"
    
    try:
        # Guardar el pedido en el sistema
        resultado = fn.guardar_pedido(chat_id, num_pedido, carrito[chat_id])
        
        if resultado:
            # Enviar confirmación al cliente
            mensaje = f"✅ *¡PEDIDO CONFIRMADO!*\n\n"
            mensaje += f"📊 *Número de pedido:* `{num_pedido}`\n"
            mensaje += f"📅 *Fecha:* {arrow.now().format("YYYYMMDD")}\n\n"  # Y aquí
            mensaje += "Tu pedido ha sido registrado correctamente.\n"
            mensaje += "Nos pondremos en contacto contigo pronto para coordinar la entrega."
            
            BOT.send_message(chat_id, mensaje, parse_mode="Markdown")
            
            # Vaciar el carrito después de confirmar
            carrito[chat_id] = []
        else:
            # Log del error
            logging.error(f"Error al guardar pedido para chat_id {chat_id}, num_pedido {num_pedido}. La función fn.guardar_pedido retornó False.")
            BOT.send_message(
                chat_id, 
                "❌ Ocurrió un error al procesar tu pedido. Por favor, contacta al administrador."
            )
    
    except Exception as e:
        # Log de la excepción completa
        logging.exception(f"Excepción al guardar pedido para chat_id {chat_id}, num_pedido {num_pedido}: {e}")
        BOT.send_message(
            chat_id, 
            "❌ Ocurrió un error inesperado al procesar tu pedido. Por favor, contacta al administrador."
        )
    
    BOT.answer_callback_query(call.id)


@BOT.callback_query_handler(func=lambda call: call.data == 'cancelar_pedido')
def cancelar_pedido(call):
    chat_id = call.message.chat.id
    
    if chat_id in carrito:
        carrito[chat_id] = []
    
    if chat_id in pedido_state:
        del pedido_state[chat_id]
    
    BOT.send_message(chat_id, "❌ Has cancelado el pedido. Tu carrito ha sido vaciado.")
    BOT.answer_callback_query(call.id)


@BOT.message_handler(func=lambda message: message.chat.id in pedido_state and pedido_state[message.chat.id] == 'esperando_termino_busqueda')
def buscar_productos_pedido(message):
    chat_id = message.chat.id
    consulta = message.text.strip()
    
    # Limpiar el estado
    del pedido_state[chat_id]
    
    if not consulta:
        BOT.send_message(chat_id, "❌ Debes ingresar un término de búsqueda.")
        return
    
    # Mensaje de espera
    wait_message = BOT.send_message(chat_id, "🔎 Buscando productos... Por favor espera.")
    
    # Realizar la búsqueda
    resultados_df = fn.buscar_producto(consulta)
    
    # Eliminar mensaje de espera
    BOT.delete_message(chat_id, wait_message.message_id)
    
    if resultados_df is not None and not resultados_df.empty:
        # Limitar a 5 resultados para no sobrecargar la interfaz
        max_resultados = min(25, len(resultados_df))
        resultados_limitados = resultados_df.head(max_resultados)
        
        BOT.send_message(
            chat_id, 
            f"✅ Se encontraron {len(resultados_df)} productos. Mostrando los primeros {max_resultados}:"
        )
        
        # Mostrar cada producto como un elemento seleccionable
        for index, row in resultados_limitados.iterrows():
            ref = str(row['REF']).strip()
            descripcion = str(row['DESCRIPCION']).strip()
            precio = float(row['PRECIO_DE_VENTA_UNITARIO'])
            stock = int(row['CONTROL_INVENTARIO'])
            
            # Preparar mensaje del producto
            mensaje = f"🏷️ *{descripcion}*\n"
            mensaje += f"📌 Ref: `{ref}`\n"
            mensaje += f"💰 Precio: ${precio:,.2f}\n"
            
            # Mostrar disponibilidad
            emoji_stock = "✅" if stock > 0 else "❌"
            mensaje += f"{emoji_stock} Stock: {stock} unidades\n"
            
            # Preparar botones según disponibilidad
            markup = types.InlineKeyboardMarkup(row_width=3)
            
            if stock > 0:
                # Botones de cantidad
                btn_1 = types.InlineKeyboardButton("1", callback_data=f'add_{ref}_1')
                btn_2 = types.InlineKeyboardButton("2", callback_data=f'add_{ref}_2')
                btn_5 = types.InlineKeyboardButton("5", callback_data=f'add_{ref}_5')
                btn_otra = types.InlineKeyboardButton("Otra cantidad", callback_data=f'add_otra_{ref}')
                
                markup.add(btn_1, btn_2, btn_5)
                markup.add(btn_otra)
            else:
                mensaje += "\n❌ *Producto sin stock disponible*"
            
            # Buscar imagen
            imagen_path = buscar_imagen(ref)
            
            if imagen_path and stock > 0:
                try:
                    with open(imagen_path, 'rb') as photo:
                        BOT.send_photo(
                            chat_id, 
                            photo, 
                            caption=mensaje, 
                            reply_markup=markup,
                            parse_mode="Markdown"
                        )
                except Exception as e:
                    BOT.send_message(
                        chat_id, 
                        mensaje, 
                        reply_markup=markup if stock > 0 else None,
                        parse_mode="Markdown"
                    )
            else:
                BOT.send_message(
                    chat_id, 
                    mensaje, 
                    reply_markup=markup if stock > 0 else None,
                    parse_mode="Markdown"
                )
        
        # Botón para buscar más productos
        markup_mas = types.InlineKeyboardMarkup()
        btn_buscar_mas = types.InlineKeyboardButton("🔍 Buscar más productos", callback_data='pedido_buscar')
        btn_ver_carrito = types.InlineKeyboardButton("🛒 Ver carrito", callback_data='ver_carrito')
        markup_mas.add(btn_buscar_mas, btn_ver_carrito)
        
        BOT.send_message(
            chat_id, 
            "¿Deseas buscar más productos o ver tu carrito?", 
            reply_markup=markup_mas
        )
    else:
        markup = types.InlineKeyboardMarkup()
        btn_buscar_otro = types.InlineKeyboardButton("🔍 Buscar otro producto", callback_data='pedido_buscar')
        btn_ver_carrito = types.InlineKeyboardButton("🛒 Ver carrito", callback_data='ver_carrito')
        markup.add(btn_buscar_otro, btn_ver_carrito)
        
        BOT.send_message(
            chat_id, 
            f"❌ No se encontraron productos con '{consulta}'.",
            reply_markup=markup
        )


@BOT.callback_query_handler(func=lambda call: call.data.startswith('add_') and not call.data.startswith('add_otra_'))
def añadir_producto_carrito(call):
    chat_id = call.message.chat.id
    
    try:
        # Extraer datos del callback
        partes = call.data.split('_')
        ref = partes[1]
        cantidad = int(partes[2])
        
        # Buscar información completa del producto
        producto = fn.obtener_info_producto(ref)
        
        if not producto:
            BOT.send_message(chat_id, f"❌ No se encontró información del producto con referencia {ref}.")
            BOT.answer_callback_query(call.id)
            return
        
        # Verificar stock
        if int(producto['stock']) < cantidad:
            BOT.send_message(
                chat_id, 
                f"❌ Stock insuficiente. Solo hay {producto['stock']} unidades disponibles."
            )
            BOT.answer_callback_query(call.id)
            return
        
        # Inicializar el carrito si no existe
        if chat_id not in carrito:
            carrito[chat_id] = []
        
        # Verificar si el producto ya está en el carrito
        producto_existente = False
        for item in carrito[chat_id]:
            if item['ref'] == ref:
                item['cantidad'] += cantidad
                producto_existente = True
                break
        
        # Si no existe, añadirlo al carrito
        if not producto_existente:
            carrito[chat_id].append({
                'ref': ref,
                'descripcion': producto['descripcion'],
                'precio': producto['precio'],
                'cantidad': cantidad
            })
        
        # Confirmar adición
        BOT.send_message(
            chat_id, 
            f"✅ Añadido al carrito: {cantidad} x {producto['descripcion']}"
        )
        
        # Mostrar opciones para continuar
        markup = types.InlineKeyboardMarkup(row_width=2)
        btn_buscar = types.InlineKeyboardButton("🔍 Seguir comprando", callback_data='pedido_buscar')
        btn_carrito = types.InlineKeyboardButton("🛒 Ver carrito", callback_data='ver_carrito')
        markup.add(btn_buscar, btn_carrito)
        
        BOT.send_message(
            chat_id, 
            "¿Qué deseas hacer ahora?", 
            reply_markup=markup
        )
        
    except Exception as e:
        print(f"Error al añadir producto: {e}")
        BOT.send_message(chat_id, "❌ Ocurrió un error al añadir el producto al carrito.")
    
    BOT.answer_callback_query(call.id)


@BOT.callback_query_handler(func=lambda call: call.data.startswith('add_otra_'))
def solicitar_cantidad_personalizada(call):
    chat_id = call.message.chat.id
    ref = call.data.split('_')[2]

    # Enviar mensaje de solicitud y guardar la información necesaria en un diccionario temporal
    mensaje = BOT.send_message(
        chat_id,
        f"📦 Introduce la cantidad que deseas para el producto con referencia {ref} (solo números):"
    )
    # Guardar ref y message_id en pedido_state
    pedido_state[chat_id] = {'state': 'esperando_cantidad', 'ref': ref, 'message_id': mensaje.message_id}  # Guardar message_id

    BOT.answer_callback_query(call.id)  # Confirmar callback inmediatamente


@BOT.message_handler(func=lambda message: message.chat.id in pedido_state and pedido_state[message.chat.id].get('state') == 'esperando_cantidad')
def procesar_cantidad_personalizada(message):
    chat_id = message.chat.id
    cantidad_texto = message.text.strip()
    estado_info = pedido_state.pop(chat_id, None)  # Obtener y eliminar estado usando chat_id

    if not estado_info:
        print(f"Error: No se encontró estado para chat_id: {chat_id}")
        BOT.send_message(chat_id, "❌ Error interno: No se pudo procesar la cantidad.")
        return

    try:
        cantidad = int(cantidad_texto)

        if cantidad <= 0:
            BOT.send_message(chat_id, "❌ La cantidad debe ser mayor que cero.")
            return

        ref = estado_info.get('ref')
        if not ref:
            print(f"Error: No se encontró referencia en estado_info: {estado_info}")
            BOT.send_message(chat_id, "❌ Error interno: No se pudo procesar la cantidad.")
            return

        # Simular callback (mejorado y simplificado)
        class MockCall:
            def __init__(self, chat_id, data):
                self.message = type('obj', (object,), {'chat': type('obj', (object,), {'id': chat_id})})
                self.data = data
                self.id = "mock_id"  # No es realmente necesario, pero se mantiene por consistencia

        mock_call = MockCall(chat_id, f'add_{ref}_{cantidad}')
        añadir_producto_carrito(mock_call)  # Reutilizar la función

    except ValueError:
        BOT.send_message(chat_id, "❌ Por favor, introduce un número válido.")
        
    except Exception as e:
        print(f" (W)Error al procesar cantidad personalizada: {e}")
        #BOT.send_message(chat_id, "❌ Ocurrió un error al procesar tu solicitud.")
#---busqueda---
def buscar_imagen(ref):
    """
    Busca una imagen correspondiente a la referencia del producto.
    Verifica diferentes extensiones comunes de imagen.
    """
    extensiones = ['.jpg', '.jpeg', '.png', '.gif', '.webp']
    
    # Primero intentamos con el nombre exacto
    for ext in extensiones:
        path = os.path.join(IMAGENES_PATH, f"{ref}{ext}")
        if os.path.exists(path):
            return path
    
    # Si no encontramos, intentamos una búsqueda menos estricta
    try:
        for filename in os.listdir(IMAGENES_PATH):
            nombre_base, extension = os.path.splitext(filename.lower())
            if ref.lower() in nombre_base:
                return os.path.join(IMAGENES_PATH, filename)
    except Exception as e:
        print(f"Error al buscar imagen para {ref}: {e}")
    
    return None

@BOT.message_handler(commands=['buscar'])
def buscar_en_inventario_telegram(message):
    chat_id = message.chat.id

    # Verificar el tipo de usuario
    tipo_usuario = fn.obtener_tipo_usuario(chat_id)

    # Si no está registrado o su tipo es menor a 2, no puede usar esta función
    if tipo_usuario is None:
        BOT.send_message(chat_id, "❌ Debes estar registrado para usar esta función. Usa /registrar para crear una cuenta.")
        return
    elif tipo_usuario < 2:
        BOT.send_message(chat_id, "⚠️ No tienes permisos suficientes para usar esta función. Esta función está disponible para usuarios tipo 2 o superior.")
        return

    consulta = message.text.split('/buscar', 1)[-1].strip()

    if not consulta:
        BOT.send_message(chat_id, "🔍 Por favor, ingresa el término que deseas buscar.\n\nEjemplo: `/buscar nombre del producto` o `/buscar REF-123`")
        return

    # Mensaje de espera mientras se realiza la búsqueda
    wait_message = BOT.send_message(chat_id, "🔎 Buscando productos... Por favor espera.")

    resultados_df = fn.buscar_producto(consulta)

    if resultados_df is not None and not resultados_df.empty:
        # Eliminamos el mensaje de espera
        BOT.delete_message(chat_id, wait_message.message_id)

        # Enviamos encabezado de resultados
        BOT.send_message(chat_id, f"✅ *RESULTADOS DE BÚSQUEDA*\n🔍 Término: `{consulta}`\n📊 Encontrados: {len(resultados_df)} productos", parse_mode="Markdown")

        # Enviamos cada producto con su imagen (si existe)
        for index, row in resultados_df.iterrows():
            # Preparamos el texto de la respuesta con emojis y formato mejorado
            respuesta = f"🏷️ *PRODUCTO {index + 1}*\n\n"

            # Añadir datos principales con emojis
            if 'REF' in row:
                respuesta += f"📌 *Referencia:* `{row['REF']}`\n"
            if 'DESCRIPCION' in row:
                respuesta += f"📝 *Descripción:* {row['DESCRIPCION']}\n"
            if 'PRECIO_DE_VENTA_UNITARIO' in row:
                precio = row['PRECIO_DE_VENTA_UNITARIO']
                precio_formateado = f"{precio:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                respuesta += f"💰 *Precio:* ${precio_formateado}\n"
            if 'CONTROL_INVENTARIO' in row:
                stock = row['CONTROL_INVENTARIO']
                emoji_stock = "✅" if stock > 0 else "❌"
                respuesta += f"{emoji_stock} *Stock:* {stock} unidades\n"

            # Añadir línea separadora
            respuesta += "\n📄 *Detalles adicionales:*\n"

            # Añadir el resto de datos
            for columna, valor in row.items():
                if columna not in ['REF', 'DESCRIPCION', 'PRECIO_DE_VENTA_UNITARIO', 'CONTROL_INVENTARIO']:
                    respuesta += f"• *{columna}:* {valor}\n"

            # Obtener la referencia del producto para buscar la imagen
            ref = str(row['REF']).strip()

            # Comprobamos si existe una imagen con ese nombre
            imagen_path = buscar_imagen(ref)

            if imagen_path:
                # Si existe imagen, la enviamos con la información del producto
                try:
                    with open(imagen_path, 'rb') as photo:
                        BOT.send_photo(chat_id, photo, caption=respuesta, parse_mode="Markdown")
                except Exception as e:
                    print(f"Error al enviar imagen {imagen_path}: {e}")
                    # Si falla, enviamos solo el texto
                    BOT.send_message(chat_id, respuesta, parse_mode="Markdown")
            else:
                # Si no hay imagen, enviamos solo el texto
                BOT.send_message(chat_id, respuesta + "\n🖼️ *Imagen no disponible*", parse_mode="Markdown")
    else:
        # Eliminamos el mensaje de espera
        BOT.delete_message(chat_id, wait_message.message_id)
        BOT.send_message(chat_id, f"❌ No se encontraron productos que coincidan con '{consulta}'.\n\n🔄 Intenta con otro término de búsqueda.")

#---registro---
@BOT.message_handler(commands=['registrar'])
def iniciar_registro(message):
    chat_id = message.chat.id
    if fn.usuario_registrado(chat_id):
        BOT.send_message(chat_id, "✅ Ya estás registrado en el sistema.")
    else:
        markup = types.InlineKeyboardMarkup()
        boton_registrar = types.InlineKeyboardButton("¡Registrarme!", callback_data='registrar_usuario')
        markup.add(boton_registrar)
        BOT.send_message(chat_id, "👋 ¿Quieres registrarte en el sistema?", reply_markup=markup)


@BOT.callback_query_handler(func=lambda call: call.data == 'registrar_usuario')
def handle_registro_button(call):
    chat_id = call.message.chat.id
    user_registration_state[chat_id] = 'esperando_nombre'
    user_data[chat_id] = {}
    BOT.send_message(chat_id, "📝 Por favor, ingresa tu nombre completo:")
    BOT.answer_callback_query(call.id)


# Este manejador solo debe activarse si no se ha activado ningún otro
@BOT.message_handler(func=lambda message: message.chat.id in user_registration_state)
def handle_user_input(message):
    chat_id = message.chat.id
    state = user_registration_state[chat_id]

    if state == 'esperando_nombre':
        user_data[chat_id]['nombre'] = message.text
        user_registration_state[chat_id] = 'esperando_telefono'
        BOT.send_message(chat_id, "📱 Ahora, por favor, ingresa tu número de teléfono:")

    elif state == 'esperando_telefono':
        user_data[chat_id]['telefono'] = message.text
        user_registration_state[chat_id] = 'esperando_correo'
        BOT.send_message(chat_id, "📧 Ingresa tu correo electrónico:")

    elif state == 'esperando_correo':
        user_data[chat_id]['correo'] = message.text
        user_registration_state[chat_id] = 'esperando_direccion'
        BOT.send_message(chat_id, "🏠 Finalmente, ingresa tu dirección:")

    elif state == 'esperando_direccion':
        user_data[chat_id]['direccion'] = message.text
        del user_registration_state[chat_id] # Limpiar el estado
        data = user_data[chat_id]
        del user_data[chat_id] # Limpiar los datos temporales
        if fn.guardar_usuario(chat_id, data['nombre'], data['telefono'], data['correo'], data['direccion']):
            BOT.send_message(chat_id, "✅ ¡Registro completado con éxito! Ahora puedes usar nuestros servicios.")
        else:
            BOT.send_message(chat_id, "❌ Hubo un problema al guardar tus datos. Por favor, intenta nuevamente.")


# Comando para ayuda
@BOT.message_handler(commands=['ayuda', 'help'])
def comando_ayuda(message):
    chat_id = message.chat.id
    tipo_usuario = fn.obtener_tipo_usuario(chat_id)
    
    mensaje = "🤖 *COMANDOS DISPONIBLES*\n\n"
    
    # Comandos básicos para todos
    mensaje += "📝 /registrar - Crear una cuenta en el sistema\n"
    mensaje += "ℹ️ /ayuda - Mostrar este mensaje de ayuda\n"
    
    # Comandos para usuarios tipo 2 o superior
    if tipo_usuario is not None and tipo_usuario >= 2:
        mensaje += "\n🔍 /buscar [término] - Buscar productos en el inventario\n"
    
    # Mensaje sobre permisos
    if tipo_usuario is None:
        mensaje += "\n⚠️ Para acceder a más funciones, regístrate usando /registrar"
    elif tipo_usuario < 2:
        mensaje += "\n⚠️ Tu nivel de acceso es limitado. Contacta al administrador para obtener más permisos."
    
    BOT.send_message(chat_id, mensaje, parse_mode="Markdown")


# Manejador de mensajes desconocidos
@BOT.message_handler(func=lambda message: True)
def mensaje_desconocido(message):
    chat_id = message.chat.id
    
    # Solo responder a mensajes que no son parte del proceso de registro
    if chat_id not in user_registration_state:
        BOT.send_message(
            chat_id, 
            "🤔 No entiendo ese comando. Usa /ayuda para ver la lista de comandos disponibles."
        )


if __name__== '__main__':
    print('Bot encendido...')
    BOT.polling(non_stop=True)