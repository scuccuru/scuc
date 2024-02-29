from bs4 import BeautifulSoup
import pandas as pd
from telegram.ext import Updater, CommandHandler, MessageHandler, ConversationHandler, CallbackQueryHandler
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Filters
import time

import re

import requests

TOKEN = '6892379980:AAHSrXsyK3QmXVFFARAj5uBvBi8xdNf_stE'
# Definire gli stati per il gestore della conversazione
AGGIUNGI_ALL_ORDINE, DECISIONE, QUANTITÀ, CONFERMA_QUANTITÀ = range(4)
PROMO_ID, NEW_ID, NEW_PRICE, FINE, CHILL= range(5)


# Inizializza la lista degli ordini e il prezzo totale
lista_ordine = []
prezzo_totale = 0

# Leggi il file Excel in un DataFrame di pandas
df = pd.read_excel('yves.xlsx')

# Definire un gestore di comando per il comando /search
def ricerca(update, context):
    update.callback_query.message.reply_text("Per favore inserisci l'ID.")
    return AGGIUNGI_ALL_ORDINE

# Definire un gestore di messaggi per catturare l'input dell'utente e cercare l'ID
def gestisci_messaggio(update, context):
    global user_input_id
    user_input_id = update.message.text
    if 'state' not in context.user_data:
      context.user_data['state'] = 'CHILL'

    if user_input_id[0].isalpha() and user_input_id[0] == 'Y':
        # Se il primo carattere è alfabetico, assumi che sia per la ricerca sul sito web
        global product_id
        product_id = user_input_id
        context.user_data['product_id'] = product_id
        url = f"https://www.yves-rocher.it/search-product/{product_id}"

        # Invia una richiesta all'URL
        response = requests.get(url)
        # Verifica se la richiesta è stata eseguita con successo
        if response.status_code == 200:
            # Analizza il contenuto HTML
            soup = BeautifulSoup(response.content, 'html.parser')

            # Trova gli elementi con la classe specificata
            product_name_elem = soup.find(class_="field--name-title")
            product_price_elem = soup.find(class_="field--name-price")

            # Verifica se entrambi gli elementi esistono
            if product_name_elem and product_price_elem:
                global product_name
                product_name = product_name_elem.get_text()
                global product_price
                product_price = product_price_elem.get_text()

                # Memorizza le informazioni sul prodotto in context.user_data
                context.user_data['product_name'] = product_name
                context.user_data['product_price'] = product_price

                # Invia un messaggio all'utente con il nome e il prezzo del prodotto
                update.message.reply_text(f"Prodotto: {product_name}\nPrezzo: {product_price}")

                # Continua chiedendo conferma
                keyboard = [[InlineKeyboardButton("Sì", callback_data='yes'),
                             InlineKeyboardButton("No", callback_data='no')]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                update.message.reply_text("Vuoi aggiungere questo articolo all'ordine?", reply_markup=reply_markup)
                return DECISIONE
            else:
                update.message.reply_text("Errore: Impossibile recuperare le informazioni sul prodotto dal sito web.")
                start(update, context)
        else:
            update.message.reply_text("Errore: Impossibile recuperare i dati dal sito web.")
            start(update, context)

          

      # Definisci la funzione per gestire il nuovo ID del prodotto
    elif context.user_data['state'] == 'PROMO_ID':
        return handle_old_id(update, context)
    elif context.user_data['state'] == 'NEW_ID':
        return handle_new_id(update, context)
    elif context.user_data['state'] == 'NEW_PRICE':
      return handle_new_price(update, context)
           
      

    elif context.user_data['state'] == 'CHILL':
        # Se il primo carattere non è alfabetico, assumi che sia per la ricerca su Excel
        try:
            user_input_id = user_input_id
            context.user_data['product_id'] = str(user_input_id)
        except ValueError:
            update.message.reply_text("ID non valido. Inserisci un ID intero valido.")
            keyboard = [[InlineKeyboardButton("Sì", callback_data='yes'),
                         InlineKeyboardButton("No", callback_data='no')]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            update.message.reply_text("Vuoi aggiungere questo articolo all'ordine?", reply_markup=reply_markup)
            return DECISIONE

        # Filtra il DataFrame in base all'ID fornito
        result = df[df['ID'] == int(user_input_id)]

        # Verifica se ci sono corrispondenze
        if not result.empty:
            # Ottieni il prezzo del prodotto dal sito web
            
            url = f"https://www.yves-rocher.it/search-product/{user_input_id}"

            # Invia una richiesta all'URL
            response = requests.get(url)
            # Verifica se la richiesta è stata eseguita con successo
            if response.status_code == 200:
                # Analizza il contenuto HTML
                soup = BeautifulSoup(response.content, 'html.parser')

                # Trova gli elementi con la classe specificata
                product_price_elem = soup.find(class_="field--name-price")

                # Verifica se l'elemento esiste
                if product_price_elem:
                    product_price = product_price_elem.get_text()

                    # Memorizza le informazioni sul prodotto in context.user_data
                    context.user_data['product_name'] = result['DESCRIZIONE'].values[0]
                    context.user_data['product_price'] = product_price

                    # Costruisci una stringa con le informazioni per l'ID corrispondente
                    reply_text = f"ID: {user_input_id}\n"
                    reply_text += f"Linea: {result['LINEA'].values[0]}\n"
                    reply_text += f"Descrizione: {result['DESCRIZIONE'].values[0]}\n"
                    reply_text += f"Prezzo Listino 2024: {result['PREZZO LISTINO 2024'].values[0]}€ . Prezzo attuale: {product_price}\n"  # Prezzo dal sito web
                    
                    update.message.reply_text(reply_text)

                    # Memorizza le informazioni sul prodotto nel contesto
                    context.user_data['product'] = result.iloc[0]

                    # Memorizza l'ID di input dell'utente per un utilizzo successivo
                    context.user_data['user_input_id'] = user_input_id

                    # Chiedi all'utente se vuole aggiungere l'articolo all'ordine
                    keyboard = [[InlineKeyboardButton("Sì", callback_data='yes'),
                                 InlineKeyboardButton("No", callback_data='no')]]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    update.message.reply_text("Vuoi aggiungere questo articolo all'ordine?", reply_markup=reply_markup)
                    return DECISIONE
                else:
                    update.message.reply_text("Errore: Impossibile recuperare il prezzo del prodotto dal sito web.")
                    start(update, context)
            else:
                update.message.reply_text("Errore: Impossibile recuperare i dati dal sito web.")
                start(update, context)
                return AGGIUNGI_ALL_ORDINE
        else:
            update.message.reply_text(f"Nessuna informazione trovata per l'ID {user_input_id}")
            start(update, context)
            return ConversationHandler.END

    return AGGIUNGI_ALL_ORDINE



# Gestisci la decisione dell'utente di aggiungere o meno l'articolo all'ordine
def gestisci_decisione(update, context):
    decisione = update.callback_query.data

    if decisione == 'yes':
        return aggiungi_all_ordine(update, context)  # Chiama la funzione aggiungi_all_ordine
    elif decisione == 'no':
        update.callback_query.message.reply_text("Articolo non aggiunto all'ordine.")
        start(update, context)
        return ConversationHandler.END

# Definisci un gestore di comando per aggiungere l'articolo all'ordine
def aggiungi_all_ordine(update, context):
    # Memorizza la decisione in user_data
    context.user_data['decisione'] = update.callback_query.data

    # Se l'utente decide di aggiungere all'ordine, procedi con la selezione della quantità
    if context.user_data['decisione'] == 'yes':
        # Chiedi all'utente di selezionare la quantità
        update.callback_query.data = ''
        keyboard = [[InlineKeyboardButton(str(i), callback_data=str(i)) for i in range(1, 11)]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        update.callback_query.message.reply_text('Seleziona la quantità:', reply_markup=reply_markup)
        return QUANTITÀ
    else:
        # Se l'utente decide di non aggiungere all'ordine, termina la conversazione
        update.callback_query.message.reply_text("Articolo non aggiunto all'ordine.")
        start(update, context)
     
        return ConversationHandler.END

# Gestisci la quantità selezionata
def gestisci_quantità(update, context):
    quantità = int(update.callback_query.data)

    # Memorizza la quantità in user_data
    context.user_data['quantità'] = quantità

    # Prosegui con la conferma della quantità
    keyboard = [[InlineKeyboardButton("Conferma", callback_data='conferma'),
                 InlineKeyboardButton("Annulla", callback_data='annulla')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.callback_query.message.reply_text(f"Conferma quantità: {quantità}?", reply_markup=reply_markup)

    return CONFERMA_QUANTITÀ

# Gestisci la conferma della quantità
def gestisci_conferma_quantità(update, context):
  global temp
  decisione = update.callback_query.data
  if decisione == 'conferma':
          query = update.callback_query
          quantità = context.user_data.get('quantità')
          prodotto = context.user_data.get('product')

          # Verifica se il prodotto è recuperato dal sito web
          if 'product_price' in context.user_data:
                # Imposta la descrizione su una stringa vuota
                descr = context.user_data.get('product_name')
                # Imposta l'ID del prodotto su user_input_data
                product_id = context.user_data.get('product_id')
                # Usa il prezzo del prodotto dal sito web
                price = context.user_data.get('product_price')
          elif temp == True:
                # Imposta la descrizione su una stringa vuota
                descr = context.user_data.get('product_name')
                # Imposta l'ID del prodotto su user_input_data
                product_id = context.user_data.get('new_id')
                # Usa il prezzo del prodotto dal sito web
                price = context.user_data.get('new_price')
          else:
                # Il prodotto è dal file Excel, usa la descrizione esistente
                descr = context.user_data.get('product_name')
                # Usa l'ID del prodotto esistente
                product_id = context.user_data.get('product_id')
                # Usa il prezzo dal file Excel
                price = prodotto.get('PREZZO LISTINO 2024', '') if prodotto else ''

          price = price.replace('€', '').replace('\xa0', '').replace(',', '.')
          prezzo_totale = round(int(quantità) * float(price), 2)

          lista_ordine.append((product_id, descr, price, quantità))
          query.edit_message_text(f"Prodotto aggiunto all'ordine.\nPrezzo totale: {prezzo_totale}")

          # Resetta i dati dell'utente
          context.user_data.clear()
          start(update, context)
          return ConversationHandler.END
  elif decisione == 'annulla':
      update.callback_query.message.reply_text("Articolo non aggiunto all'ordine.")
      start(update, context)
      return ConversationHandler.END

# Definisci un gestore di comando per il comando /order
def ordine(update, context):
  if not lista_ordine:
      update.callback_query.message.reply_text("Il tuo ordine è vuoto.")
      start(update, context)
  else:
      testo_ordine = "Il tuo ordine attuale:\n"
      tot = 0.0
      for articolo in lista_ordine:
          testo_ordine += f"ID: {articolo[0]}, Descrizione: {articolo[1]}, Prezzo: {articolo[2]}€, Quantità: {articolo[3]}\n"
          tot += float(articolo[2]) * int(articolo[3]) # Converti articolo[2] in float prima di aggiungere
      update.callback_query.message.reply_text(testo_ordine)
      update.callback_query.message.reply_text(f"Il totale dell'ordine è: {round(tot,2)}€")
      start(update, context)

# Definisci un gestore di comando per il comando /clearorder
def cancella_ordine(update, context):
    global lista_ordine
    lista_ordine = []  # Cancella la lista degli ordini
    update.callback_query.message.reply_text("Ordine cancellato con successo.")
    start(update, context)

def modifica_ordine(update, context):
  global check
  if not lista_ordine:
      update.callback_query.message.reply_text("Il tuo ordine è vuoto.")
      return

  # Loop through each product in the order
  for articolo in lista_ordine:
      id_prodotto = articolo[0]
      descrizione = articolo[1]
      quantita = int(articolo[3])
      check+=1

      # Initialize the keyboard for each product
      keyboard = []

      # Create inline buttons for each quantity from 1 to the current quantity in the order
      for i in range(0, quantita + 1):
          buttons_row = [InlineKeyboardButton(str(i), callback_data=f'remove_{id_prodotto}_{i}')]
          keyboard.append(buttons_row)

      reply_markup = InlineKeyboardMarkup(keyboard)
      update.callback_query.message.reply_text(f"Seleziona la quantità da rimuovere per questo articolo:\n ID: {id_prodotto}\n Descrizione: {descrizione}", reply_markup=reply_markup)

# Define a callback handler to handle the user's selection
def remove_quantity(update, context):
  global modified_count
  global check
  query = update.callback_query
  data = query.data.split('_')  # Extracting data from callback data

  if len(data) != 3:
      query.answer("Errore nella selezione della quantità da rimuovere.")
      return

  id_prodotto = data[1]
  quantita_da_rimuovere = int(data[2])

  # Variable to keep track of the number of products modified
  

  # Find and update the quantities for all matching product IDs
  for i, articolo in enumerate(lista_ordine):
      if str(articolo[0]) == id_prodotto:  # Ensure consistent treatment of product IDs as strings
          nuova_quantita = int(articolo[3]) - quantita_da_rimuovere
          if nuova_quantita <= 0:
              del lista_ordine[i]  # Remove the item if the new quantity is 0 or negative
          else:
              nuovo_articolo = (articolo[0], articolo[1], articolo[2], str(nuova_quantita))
              lista_ordine[i] = nuovo_articolo  # Update the quantity

          modified_count += 1  # Increment the modified count

  if modified_count > 0:
      query.edit_message_text(f"Quantità: {quantita_da_rimuovere}\nRimossa dall'ordine per il prodotto {id_prodotto} con successo.")

  # Check if all modifications are completed
  if   modified_count == check:
      start(update, context)  # Call start function if all modifications are completed
  else:
      query.answer("Seleziona la quantità da rimuovere per un altro articolo.")  # Prompt for next modification






def save_order_to_file():
  file_path = 'order.txt'
  with open(file_path, 'w') as file:
      for articolo in lista_ordine:
          file.write(f"{str(articolo[0])}|{articolo[1]}|{articolo[2]}|{articolo[3]}\n")
        
# Define a function to load the order data from a text file
def load_order_from_file():
    file_path = 'order.txt'
    try:
        with open(file_path, 'r') as file:  # Open the file in read mode
            lines = file.readlines()  # Read all lines from the file
            for line in lines:
                # Split each line into fields and add to lista_ordine
                articolo = line.strip().split('|')
                lista_ordine.append((articolo[0], articolo[1], articolo[2], articolo[3]))
    except FileNotFoundError:
        # Handle the case where the file does not exist
        print("File not found. No order data loaded.")



  # Definisci la funzione per avviare la promozione del prodotto
def start_promotion(update, context):
      context.user_data['state'] = 'PROMO_ID'
      update.callback_query.message.reply_text("Benvenuto alla promozione del prodotto! Inserisci l'ID del vecchio prodotto:")
      return PROMO_ID

  # Definisci la funzione per gestire l'ID del vecchio prodotto
def handle_old_id(update, context):
      context.user_data['state'] = 'NEW_ID'
      
      # Recupera l'ID del vecchio prodotto inserito dall'utente
      old_id = update.message.text
      # Usa la funzione handle_message per recuperare la descrizione e la linea del prodotto
      # Salva queste informazioni per l'uso successivo
      context.user_data['old_id'] = old_id
      update.message.reply_text("Ottimo! Ora inserisci il nuovo ID del prodotto (formato: L seguito da numeri):")
      return NEW_ID

  # Definisci la funzione per gestire il nuovo ID del prodotto
def handle_new_id(update, context):
      context.user_data['state'] = 'NEW_PRICE'
      # Recupera il nuovo ID del prodotto inserito dall'utente
      new_id = update.message.text
      # Verifica se il nuovo ID ha il formato corretto
      if not new_id.startswith('L'):
          update.message.reply_text("Il nuovo ID deve iniziare con 'L'. Per favore inserisci un nuovo ID valido.")
          context.user_data['state'] = 'NEW_ID'
          return NEW_ID
      # Salva il nuovo ID per l'uso successivo
      context.user_data['new_id'] = new_id
      update.message.reply_text("Ottimo! Ora inserisci il nuovo prezzo scontato del prodotto:")
      return NEW_PRICE

  # Definisci la funzione per gestire il nuovo prezzo scontato del prodotto
def handle_new_price(update, context):
      global temp
      # Recupera il nuovo prezzo scontato del prodotto inserito dall'utente
      new_price = update.message.text
      # Salva il nuovo prezzo per l'uso successivo
      context.user_data['new_price'] = new_price
      update.message.reply_text("Promozione completata! Ora puoi aggiungere il prodotto all'ordine.")
      
      result = df[df['ID'] == context.user_data['old_id']]
      try:
        user_input_id =  context.user_data['old_id']
        print(user_input_id)
        context.user_data['product_id'] =  context.user_data['new_id']
      except ValueError:
        update.message.reply_text("ID non valido. Inserisci un ID intero valido.")
        keyboard = [[InlineKeyboardButton("Sì", callback_data='yes'),
                     InlineKeyboardButton("No", callback_data='no')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        update.message.reply_text("Vuoi aggiungere questo articolo all'ordine?", reply_markup=reply_markup)
        return DECISIONE

      result = df[df['ID'] == int(context.user_data['old_id'])]
      reply_text = f"ID: {context.user_data['new_id']}\n"
      reply_text += f"Linea: {result['LINEA'].values[0]}\n"
      reply_text += f"Descrizione: {result['DESCRIZIONE'].values[0]}\n"
      reply_text += f"Prezzo Listino 2024: {result['PREZZO LISTINO 2024'].values[0]}. Prezzo Promozionale: {context.user_data['new_price']}\n"  # Prezzo dal sito web

      update.message.reply_text(reply_text)
      context.user_data['product_name'] = result['DESCRIZIONE'].values[0]
      temp = True

      # Memorizza le informazioni sul prodotto nel contesto
      context.user_data['product'] = result.iloc[0]

      # Memorizza l'ID di input dell'utente per un utilizzo successivo
      context.user_data['user_input_id'] = user_input_id

      # Chiedi all'utente se vuole aggiungere l'articolo all'ordine
      keyboard = [[InlineKeyboardButton("Sì", callback_data='yes'),
                   InlineKeyboardButton("No", callback_data='no')]]
      reply_markup = InlineKeyboardMarkup(keyboard)
      update.message.reply_text("Vuoi aggiungere questo articolo all'ordine?", reply_markup=reply_markup)
      return DECISIONE

      

      # Ritorna al normale flusso di aggiunta di prodotti all'ordine
      

  # Registra il gestore della conversazione della promozione nel dispatcher



def start(update, context):
  global modified_count
  modified_count = 0
  global check
  check = 0
  global temp 
  temp = False
  if 'state' not in context.user_data:
    context.user_data['state'] = 'CHILL'
 
  if update.message:
      # Call the load_order_from_file function to populate lista_ordine
      lista_ordine = []
      load_order_from_file()
      keyboard = [
          [InlineKeyboardButton("Cerca", callback_data='search')],
          [InlineKeyboardButton("Ordine", callback_data='order')],
          [InlineKeyboardButton("Cancella Ordine", callback_data='clearorder')],
          [InlineKeyboardButton("Modifica Ordine", callback_data='modifica_ordine')],
          [InlineKeyboardButton("Promozione", callback_data='promozione')]
        ]
      
      reply_markup = InlineKeyboardMarkup(keyboard)
      update.message.reply_text('Benvenuto! Cosa desideri fare?', reply_markup=reply_markup)
      return ConversationHandler.END
  else: 
      save_order_to_file()
      keyboard = [
        [InlineKeyboardButton("Cerca", callback_data='search')],
        [InlineKeyboardButton("Ordine", callback_data='order')],
        [InlineKeyboardButton("Cancella Ordine", callback_data='clearorder')],
        [InlineKeyboardButton("Mofiica Quantità", callback_data='modifica_ordine')],
        [InlineKeyboardButton("Promozione", callback_data='promozione')],
        [InlineKeyboardButton("Termina", callback_data='toggle')]
      ]
      reply_markup = InlineKeyboardMarkup(keyboard)
      context.bot.send_message(update.callback_query.from_user.id, 'Quale altra operazione desideri eseguire?', reply_markup=reply_markup)
      return ConversationHandler.END
    


# Definisci la funzione per gestire le callback query
def button(update, context):
  query = update.callback_query
  if query.data == 'search':
      ricerca(update, context)
  elif query.data == 'order':
      ordine(update, context)
  elif query.data == 'clearorder':
      cancella_ordine(update, context)
  elif query.data == 'modifica_ordine':
    modifica_ordine(update, context)
  elif query.data == 'promozione':
    start_promotion(update, context)
  elif query.data == 'toggle':
        toggle_bot(update, context)
  else:
      # Se l'oggetto update non contiene un messaggio, esci dalla funzione
      return

  # Controlla se update contiene un messaggio
  if update.message:
      update.message.reply_text("Operazione completata.")
  else:
      query.answer()  # Rispondi alla callback_query

def toggle_bot(update, context):
    global bot_attivo
    bot_attivo = not bot_attivo
    if bot_attivo:
        update.message.reply_text("Bot attivato!")
    else:
        update.message.reply_text("Bot disattivato.")


updater = Updater(TOKEN, use_context = True)
dispatcher = updater.dispatcher

# Registra il gestore di callback query nel dispatcher
dispatcher.add_handler(CallbackQueryHandler(button, pattern='^(search|order|clearorder|modifica_ordine|promozione|toggle)$'))
# Registra la nuova funzione come gestore di comando per il comando /start
dispatcher.add_handler(CommandHandler('start', start))

# Registra un gestore di messaggi per catturare l'input dell'utente
dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, gestisci_messaggio))

dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_old_id))

dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_new_id))

dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_new_price))
# Registra un gestore di callback query per gestire la decisione (Sì/No)
dispatcher.add_handler(CallbackQueryHandler(gestisci_decisione, pattern='^(yes|no)$'))

# Registra un gestore di callback query per gestire la selezione della quantità
dispatcher.add_handler(CallbackQueryHandler(gestisci_quantità, pattern='^[0-9]+$'))

dispatcher.add_handler(CallbackQueryHandler(gestisci_conferma_quantità, pattern='^(conferma|annulla)+$'))
dispatcher.add_handler(CallbackQueryHandler(modifica_ordine,pattern='^[0-9]+$'))

# Definisci un gestore di conversazione per gestire la decisione di aggiungere l'articolo all'ordine
gestore_conversazione = ConversationHandler(
    entry_points=[CommandHandler('search', ricerca)],
    states={
        AGGIUNGI_ALL_ORDINE: [MessageHandler(Filters.text & ~Filters.command, gestisci_messaggio)],
        DECISIONE: [CallbackQueryHandler(gestisci_decisione)],  # Cambia in gestisci_decisione
        QUANTITÀ: [CallbackQueryHandler(gestisci_quantità)],  # Cambia in gestisci_quantità
        CONFERMA_QUANTITÀ: [CallbackQueryHandler(gestisci_conferma_quantità)]
    },
    fallbacks=[]
)




  # Aggiungi il gestore della conversazione della promozione al dispatcher

dispatcher.add_handler(CommandHandler('modifica_ordine', modifica_ordine))

# Register the callback handler to handle the user's selection
dispatcher.add_handler(CallbackQueryHandler(remove_quantity))
# Aggiungi il gestore della conversazione al dispatcher
dispatcher.add_handler(gestore_conversazione)


while True:
    try:
        updater.start_polling()
        break  # Exit the loop if polling starts successfully
    except Conflict as e:
        logging.error(f"Conflict error: {e}")
        logging.info("Retrying in 5 seconds...")
        time.sleep(5)  # Wait for 5 seconds before retrying

# Run the bot until you press Ctrl-C
updater.idle()


