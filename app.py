from flask import Flask, request, jsonify, render_template
import pymysql
import openai, time, webbrowser
from datetime import datetime, timedelta
import stripe
from twilio.twiml.messaging_response import MessagingResponse
import pyshorteners

stripe.api_key ="stripe_api_key"

app = Flask(__name__)


openai.api_key = 'Your_Api_key'

config = {
    'host': 'localhost',
    'user': 'root',
    'password': '',
    'database': 'user',
}

# user_conversations = {}
# print(user_conversations)

def has_user_interacted_before(phone):
    conn = pymysql.connect(**config)
    cursor = conn.cursor()

    select_query = "SELECT COUNT(*) FROM history WHERE user_id = (SELECT id FROM userdata WHERE phone = %s)"
    cursor.execute(select_query, (phone,))
    interaction_count = cursor.fetchone()[0]

    cursor.close()
    conn.close()

    return interaction_count > 0

def register_user(phone):
    conn = pymysql.connect(**config)
    cursor = conn.cursor()

    insert_query = "INSERT INTO userdata (phone,  trial_start_timestamp) VALUES (%s,%s)"
    trial_expiry = datetime.now() + timedelta(days=7)
    cursor.execute(insert_query, (phone,trial_expiry))
    conn.commit()

    user_id = cursor.lastrowid
    print(f"User registered - ID: {user_id}, Phone: {phone}")

    cursor.close()
    conn.close()

    return user_id


@app.route('/order/success', methods=['GET'])
def order_success():
    
    return render_template('index.html')

@app.route('/ask', methods=['POST'])
def ask_question():
    
    question = request.values.get('Body', '').lower()
    phone_numeric = request.values.get('From', '')
    phone = ''.join(filter(str.isdigit, phone_numeric))
    print(phone)   
    print("Question: ", question)

    if not phone or not question:
        return jsonify({'error': 'Phone number and question are required.'}), 400

    conn = pymysql.connect(**config)
    cursor = conn.cursor()
    select_query = "SELECT * FROM userdata WHERE phone = %s"

    cursor.execute(select_query, (phone,))
    user_data = cursor.fetchone()
 

    if not user_data:
        
        user_id = register_user(phone)
        

    if not has_user_interacted_before(phone):
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        bot_resps = MessagingResponse()
        msg = bot_resps.message()
        msg.body("Welcome to TextEli \nPlease review our terms of servive at www.texteli.ai/tos. Standard message and data rates may apply according to your mobile carrier's plan. Respond 'YES' to continue and accept the terms of service. Thank you for using TextEli and happy chatting")
        chat="Welcome to TextEli \nPlease review our terms of servive at www.texteli.ai/tos. Standard message and data rates may apply according to your mobile carrier's plan. Respond 'YES' to continue and accept the terms of service. Thank you for using TextEli and happy chatting"
        conn = pymysql.connect(**config)
        cursor = conn.cursor()
        insert_query = "INSERT INTO history (user_id, question, answer, timestamp) VALUES (%s, %s, %s, %s)"
        cursor.execute(insert_query, (user_id, question, chat, timestamp))
        conn.commit()

        cursor.close()
        conn.close()

        return str(bot_resps)
    else:

        user_id = user_data[0] 
        trial_start_timestamp = user_data[3]
        print(trial_start_timestamp)

        cursor.execute("SELECT question FROM history WHERE user_id = %s", (user_id,))
        interaction_count = cursor.rowcount
        print(interaction_count)

        if interaction_count == 1:
            if question == "yes":
                timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                conn = pymysql.connect(**config)
                cursor = conn.cursor()
                chat = "thanks for accepting"
                insert_query = "INSERT INTO history (user_id, question, answer, timestamp) VALUES (%s, %s, %s, %s)"
                cursor.execute(insert_query, (user_id, question, chat, timestamp))
                
                conn.commit()
                cursor.close()
                conn.close()
                bot_resps = MessagingResponse()
                msg = bot_resps.message()
                msg.body("Thanks for your response! You now have a 7-day free trial to explore our services. Enjoy!")
                return str(bot_resps)
            else:
                # Delete user details since the second message wasn't "yes"
                conn = pymysql.connect(**config)
                cursor = conn.cursor()
                delete_query = "DELETE FROM userdata WHERE id = %s"
                cursor.execute(delete_query, (user_id,))
                conn.commit()
                bot_resps = MessagingResponse()
                msg = bot_resps.message()
                msg.body("Thanks for your response. If you change your mind and want to use our service, feel free to message again. Have a great day!")
                return str(bot_resps)
        
        trial_start_timestamp = datetime.strptime(trial_start_timestamp, '%Y-%m-%d %H:%M:%S.%f')
        print("after else",trial_start_timestamp)

        # Calculate the elapsed time since trial start
        current_timestamp = datetime.now()
        print("current timestamp", current_timestamp)

        elapsed_time = trial_start_timestamp - current_timestamp
        print("remaining time", elapsed_time)

        elapsed_seconds = int(elapsed_time.total_seconds())
        print(elapsed_seconds)

        

        if elapsed_seconds <= 0:   

            session = stripe.checkout.Session.create(
            
                line_items=[
                    {
                        'price': "price_1NiKfUSBalEG4xpcqKrTujiz",
                        'quantity': 1,
                    },
                ],
                payment_method_types=['card'],
                mode='subscription',
                success_url='https://yourwebsite.com/success',  
                cancel_url='https://yourwebsite.com/cancel',   
                subscription_data={
                "metadata": {'phone': phone},
                "trial_settings": {"end_behavior": {"missing_payment_method": "cancel"}}
            },
            payment_method_collection="if_required",
            )
            print(phone)

            payment_url = session.url
            print("monthly payment",payment_url)

#++++++++++++++++ second payment link++++++++++++++++

            session = stripe.checkout.Session.create(
            
                line_items=[
                    {
                        'price': "price_1Nk1OISBalEG4xpcnP6YQCiT",
                        'quantity': 1,
                    },
                ],
                payment_method_types=['card'],
                mode='subscription',
                success_url='https://yourwebsite.com/success',  
                cancel_url='https://yourwebsite.com/cancel',   
                subscription_data={
                "metadata": {'phone': phone},
                "trial_settings": {"end_behavior": {"missing_payment_method": "cancel"}}
            },
            payment_method_collection="if_required",
            )
            print("second",phone)

            payment_url2 = session.url
            print("yearly pament",payment_url2)
            
            
            # short_url = "https://texteli.net/recharge-stripe"
            
            s = pyshorteners.Shortener()


            first_short_url = s.tinyurl.short(payment_url)
            second_short_url = s.tinyurl.short(payment_url2)
            print("short url:",first_short_url)
            print("short url:",second_short_url)


#++++++++++bot response when payment occur+++++++++++++++
            
            bot_resps = MessagingResponse()
            msg = bot_resps.message()
            msg.body("You've used your free 7 days trial. Now, enhance your experience by recharging through the link below:\n" + "Upgrade your experience with our Monthly Subscription! Gain access to exclusive features and stay connected with our AI-powered chat 24/7. Start enjoying the benefits today:\n " +first_short_url  + "\nLooking for even more value? Consider our Yearly Subscription! Get a full year of uninterrupted access, continuous improvements, and endless possibilities. Don't miss out! \n" + second_short_url)
            
            return str(bot_resps)
            # return render_template("recharge.html", url_first=payment_url, url_second =payment_url2)
            
            
    cursor.execute("SELECT question, answer FROM history WHERE user_id = %s ORDER BY timestamp DESC LIMIT 2",(user_id,))
    chat_history = cursor.fetchall()   
    cursor.close()
    conn.close()


    # Preprocess the chat history and format it as messages
    preprocessed_history = []
    
    for entry in reversed (chat_history):
        preprocessed_history.append({"role": "user", "content": entry[0]})
        preprocessed_history.append({"role": "assistant", "content": entry[1]})

    # Add the new message to the preprocessed history
    user_message = {"role": "user", "content": question}
    preprocessed_history.append(user_message)
    print(preprocessed_history)

    try:
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
      
        response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo-16k",
                messages=preprocessed_history
                )

        chat_response = response.choices[0].message.content.strip()
        a = len(chat_response)
        print("length",a)

        
        chunk_size = 1500  # Define the size of each chunk
        response_chunks = [chat_response[i:i + chunk_size] for i in range(0, len(chat_response), chunk_size)]

        bot_resp = MessagingResponse()
        
        for chunk in response_chunks:   
            print("hello",chunk)    
            msg = bot_resp.message()
            msg.body(chunk)  
        
        conn = pymysql.connect(**config)
        cursor = conn.cursor()

        insert_query = "INSERT INTO history (user_id, question, answer, timestamp) VALUES (%s, %s, %s, %s)"
        cursor.execute(insert_query, (user_id, question, chat_response, timestamp))
        conn.commit()

        cursor.close()
        conn.close()

        return str(bot_resp)      

    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
@app.route('/stripe_webhook', methods=['POST'])
def stripe_webhook():
    payload = request.get_json()
    event = None

    try:
        event = stripe.Event.construct_from(payload, stripe.api_key)
    except ValueError as e:
       
        return jsonify({"error": str(e)}), 400

    if event.type == 'invoice.payment_succeeded':
        # Extract subscription ID
        subscription_id = event['data']['object']['subscription']
        subscription = stripe.Subscription.retrieve(subscription_id)
        
        # You can now use the transaction_id and status as needed
        phone_number = subscription.metadata.get('phone')
        period_end_date = subscription.current_period_end

        print(f"User Phone: {phone_number}")
        print("Period End Date:", period_end_date)

        formatted_date = datetime.fromtimestamp(period_end_date).strftime('%Y-%m-%d %H:%M:%S.%f')


        print("Formatted Date:", formatted_date)

        conn = pymysql.connect(**config)
        cursor = conn.cursor()
        select_query = "SELECT * FROM userdata WHERE phone = %s"
        cursor.execute(select_query, (phone_number,))
        user_data = cursor.fetchone()

        if user_data:
            user_id = user_data[0]
            print(user_id)

            update_query = "UPDATE userdata SET trial_start_timestamp = %s WHERE phone = %s"
            update_params = (formatted_date, phone_number)  # Tuple of parameters

            cursor.execute(update_query, update_params)

            # Update the transaction table with payment_intent_id and user_id
            insert_query = "INSERT INTO transaction (user_id, transaction_id, phone) VALUES (%s, %s, %s)"
            cursor.execute(insert_query, (user_id, subscription_id, phone_number))


            
            conn.commit()

        cursor.close()
        conn.close()       
        
    # print(session)
    return jsonify({"status": "success"}), 200

if __name__ == '__main__':
    app.run(debug=True)



