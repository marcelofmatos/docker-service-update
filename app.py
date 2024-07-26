from flask import Flask, request, jsonify
import docker

app = Flask(__name__)
client = docker.from_env()

@app.route('/update_services', methods=['POST'])
def update_services():
    data = request.json
    image_name = data.get('image_name')

    if not image_name:
        return jsonify({'error': 'image_name is required'}), 400

    try:
        services = client.services.list()
        updated_services = []

        for service in services:
            service_info = service.attrs
            service_image = service_info['Spec']['TaskTemplate']['ContainerSpec']['Image']

            if image_name in service_image:
                service.update(image=image_name)
                # Adiciona o nome do serviço ao invés do ID
                updated_services.append(service.name)

        return jsonify({
            'message': 'Services updated successfully',
            'updated_services': updated_services
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80)
