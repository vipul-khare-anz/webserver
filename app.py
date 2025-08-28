import base64
from io import BytesIO

import boto3
from PIL import Image
from flask import Flask, render_template, request, redirect, make_response, Response

app = Flask(__name__)

# SQS queue to receive messages
img_input_queue_url = "https://sqs.eu-south-2.amazonaws.com/590183679875/web-queue"
# SQS queue to send messages
img_output_queue_url = "https://sqs.eu-south-2.amazonaws.com/590183679875/application-queue"

region_name = "eu-south-2"


@app.route('/')
def home():
    return render_template('home.html')


@app.route('/', methods=['POST'])
def upload_image():
    if 'file' not in request.files:
        print('No file part')
        return redirect(request.url)
    file = request.files['file']
    print(file.filename)
    img = Image.open(file.stream)
    buffered = BytesIO()
    img.save(buffered, format="JPEG")
    img_str = base64.b64encode(buffered.getvalue()).decode()
    sqs = boto3.client('sqs',region_name=region_name)

    # Send message to SQS queue
    response = sqs.send_message(
        QueueUrl=img_input_queue_url,
        # The length of time, in seconds, for which the delivery of all messages in the queue is delayed
        DelaySeconds=5,
        MessageBody=img_str
    )

    print(response['MessageId'])
    return redirect(request.url)


@app.route('/view', methods=['GET'])
def retrieve_img():
    res = {}
    sqs = boto3.client('sqs',region_name=region_name)
    response = sqs.receive_message(
        QueueUrl=img_output_queue_url,
        MaxNumberOfMessages=1,
        MessageAttributeNames=[
            'All'
        ],
        VisibilityTimeout=30,
        WaitTimeSeconds=0
    )
    messages = response.get("Messages", [])
    for message in messages:
        res["dec_str"] = message["Body"]
        receipt_handle = message['ReceiptHandle']
        # Delete received message from queue
        sqs.delete_message(
            QueueUrl=img_output_queue_url,
            ReceiptHandle=receipt_handle
        )

    if len(res) < 1:
        return "fail", 400
    else:
        response = make_response(res["dec_str"])
        response.headers.set('Content-Type', 'image/gif')
        response.headers.set('Content-Disposition', 'attachment', filename='image.gif')
        return response


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=80, debug=True)
