from flask import Flask, request, jsonify, render_template
import pymysql
import openai, time, webbrowser
from datetime import datetime
import stripe
from twilio.twiml.messaging_response import MessagingResponse

stripe.api_key ="sk_test_51NU5fgSBalEG4xpc1ZcvQ6J21MRGDpo424i7DXBFrU7xqmvzOBlHtbcND0fd39nTIS3vL1q4ODtW5Yj8SjOEM1lT0086Mjs9rc"

app = Flask(__name__)


openai.api_key = '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'

config = {
    'host': 'localhost',
    'user': 'root',
    'password': '',
    'database': 'user',
}

# user_conversations = {}
# print(user_conversations)

def register_user(phone):
    conn = pymysql.connect(**config)
    cursor = conn.cursor()

    insert_query = "INSERT INTO userdata (phone, token) VALUES (%s,%s)"
    cursor.execute(insert_query, (phone, 100))
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
    
    # if phone in user_conversations:
    #     conversation = user_conversations[phone]
    # else:
    #     conversation = []
    #     user_conversations[phone] = conversation

    conn = pymysql.connect(**config)
    cursor = conn.cursor()
    select_query = "SELECT * FROM userdata WHERE phone = %s"

    cursor.execute(select_query, (phone,))
    user_data = cursor.fetchone()
 

    if not user_data:
        # Register the phone number if it is not present in the userdata table
        user_id = register_user(phone)
        token = 5000
    else:
        user_id = user_data[0]
        token = user_data[2] 
        
        if token <= 0:
            session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=[{
                    'price': 'price_1NUpksSBalEG4xpcfh7is0M7',  # Replace with your price ID
                    'quantity': 1,
                }],
                mode='payment',
                metadata={
                    'phone': phone  # Include the phone number in the metadata
                },
                success_url='http://127.0.0.1:5000/order/success'
                ,  # Replace with your success URL
                cancel_url='https://your_domain.com/cancel'  # Replace with your cancel URL
            )

            payment_url = session.url
            
            print(payment_url)
            bot_resps = MessagingResponse()
            msg = bot_resps.message()
            msg.body("Unlock the limitless potential of our AI-powered chat by simply recharging through Stripe. ⚡️💳 Embrace the magic of meaningful interactions and let your imagination soar! Tap the link below to supercharge your chat experience: Recharge Now! Happy chatting! 🎉✨" + "  " +payment_url)
            return str(bot_resps)
    cursor.execute(
        "SELECT question, answer FROM history WHERE user_id = %s ORDER BY timestamp DESC LIMIT 2",
        (user_id,)
    )
    chat_history = cursor.fetchall()   
    cursor.close()
    conn.close()

    # conn = pymysql.connect(**config)
    # cursor = conn.cursor()
    # select_query = "SELECT * FROM history WHERE user_id = %s ORDER BY timestamp DESC LIMIT 3"
    # cursor.execute(select_query, (user_id,))
    # chat_history = cursor.fetchall()
    # cursor.close()
    # conn.close()

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
    
        # user_message = {"role": "user", "content": question}
        # conversation.append(user_message)
        # print("++++++++++++++++++++++++++++++++")
        # print(conversation)
        # conversationss= conversation[-4:]
        # print("+++++++++++++conversationsssssss++++++++++++")
        # print(conversationss)

        response = openai.ChatCompletion.create(
                        model="gpt-3.5-turbo-16k",
                        messages=preprocessed_history,
                        max_tokens =100
                    )

        chat_response = response.choices[0].message.content.strip()
        print(chat_response)
        print("hekloo")
        a = len(chat_response)
        print(a)
        bot_resp = MessagingResponse()
        msg = bot_resp.message()
        msg.body(chat_response)      
        
        usage = response["usage"]["total_tokens"]
        print("++++++token used++++++++")
        print(usage)
        updated_token = max(token - usage, 0)

        conn = pymysql.connect(**config)
        cursor = conn.cursor()

        update_query = "UPDATE userdata SET token = %s WHERE phone = %s"
        cursor.execute(update_query, (updated_token, phone))
     
        insert_query = "INSERT INTO history (user_id, question, answer, timestamp) VALUES (%s, %s, %s, %s)"
        cursor.execute(insert_query, (user_id, question, chat_response, timestamp))
        conn.commit()

        cursor.close()
        conn.close()

        # system_message = {"role": "assistant", "content": chat_response}
        # conversation.append(system_message)
        # print("+++++++++++++prompt and response +++++")
        # print(conversation)

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
   
    if event.type == 'checkout.session.completed':
        # Payment session completed, you can access the data like this:
        session = event.data.object
        payment_intent_id = session['payment_intent']
        print(payment_intent_id)

        phone_number = payload['data']['object']['metadata'].get('phone')
        print(f"User Phone: {phone_number}")

        conn = pymysql.connect(**config)
        cursor = conn.cursor()
        select_query = "SELECT * FROM userdata WHERE phone = %s"
        cursor.execute(select_query, (phone_number,))
        user_data = cursor.fetchone()

        if user_data:
            user_id = user_data[0]
            print(user_id)

            # Update the transaction table with payment_intent_id and user_id
            insert_query = "INSERT INTO transaction (user_id, transaction_id, phone) VALUES (%s, %s, %s)"
            cursor.execute(insert_query, (user_id, payment_intent_id, phone_number))

            update_query = "UPDATE userdata SET token = 5000 WHERE phone = %s"
            cursor.execute(update_query, (phone_number,))
            
            conn.commit()

        cursor.close()
        conn.close()       
        
    # print(session)
    return jsonify({"status": "success"}), 200

if __name__ == '__main__':
    app.run(debug=True)



