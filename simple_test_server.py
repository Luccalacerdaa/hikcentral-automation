#!/usr/bin/env python3
"""
Servidor de teste simples que simula a automação HikCentral
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import json
import threading
import time
from datetime import datetime
import logging

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

app = Flask(__name__)
CORS(app)

# Configurações
API_KEY = "test-key-123"
PORT = 5001

# Armazenar status das automações
automation_status = {}
automation_lock = threading.Lock()

class MockAutomationManager:
    def __init__(self):
        self.is_running = False
        self.current_visitor_id = None
        
    def start_automation(self, visitor_id, visitor_data):
        """Simula o início de uma automação"""
        if self.is_running:
            return False, "Já existe uma automação em andamento"
        
        try:
            self.current_visitor_id = visitor_id
            self.is_running = True
            
            # Atualizar status
            with automation_lock:
                automation_status[visitor_id] = {
                    'status': 'running',
                    'started_at': datetime.now().isoformat(),
                    'step': 'initializing',
                    'message': 'Iniciando automação...'
                }
            
            # Simular automação em thread separada
            thread = threading.Thread(
                target=self._simulate_automation,
                args=(visitor_id, visitor_data)
            )
            thread.daemon = True
            thread.start()
            
            return True, "Automação iniciada com sucesso"
            
        except Exception as e:
            self.is_running = False
            self.current_visitor_id = None
            logging.error(f"Erro ao iniciar automação: {e}")
            return False, str(e)
    
    def _simulate_automation(self, visitor_id, visitor_data):
        """Simula a execução da automação"""
        try:
            logging.info(f"🚀 Simulando automação para visitante {visitor_id}")
            
            # Simular configuração do driver
            with automation_lock:
                automation_status[visitor_id]['step'] = 'setup_driver'
                automation_status[visitor_id]['message'] = 'Configurando Chrome...'
            
            time.sleep(2)  # Simular tempo de configuração
            
            # Simular login
            with automation_lock:
                automation_status[visitor_id]['step'] = 'login'
                automation_status[visitor_id]['message'] = 'Fazendo login no HikCentral...'
            
            time.sleep(3)  # Simular tempo de login
            
            # Simular navegação
            with automation_lock:
                automation_status[visitor_id]['step'] = 'navigation'
                automation_status[visitor_id]['message'] = 'Navegando para formulário...'
            
            time.sleep(2)  # Simular tempo de navegação
            
            # Simular preenchimento
            with automation_lock:
                automation_status[visitor_id]['step'] = 'filling_form'
                automation_status[visitor_id]['message'] = 'Preenchendo formulário...'
            
            time.sleep(4)  # Simular tempo de preenchimento
            
            # Simular resultado (80% de sucesso)
            import random
            success = random.random() > 0.2  # 80% de chance de sucesso
            
            with automation_lock:
                if success:
                    automation_status[visitor_id] = {
                        'status': 'completed',
                        'started_at': automation_status[visitor_id]['started_at'],
                        'completed_at': datetime.now().isoformat(),
                        'step': 'completed',
                        'message': 'Automação concluída com sucesso',
                        'result': {
                            'success': True,
                            'message': f'Visitante {visitor_data["name"]} cadastrado com sucesso',
                            'hikcentral_id': f'HK{visitor_id[-6:]}',
                            'timestamp': datetime.now().isoformat()
                        }
                    }
                    logging.info(f"✅ Automação simulada concluída com sucesso para visitante {visitor_id}")
                else:
                    automation_status[visitor_id] = {
                        'status': 'failed',
                        'started_at': automation_status[visitor_id]['started_at'],
                        'completed_at': datetime.now().isoformat(),
                        'step': 'failed',
                        'message': 'Falha na automação: Elemento não encontrado',
                        'result': {
                            'success': False,
                            'error': 'Elemento não encontrado no formulário',
                            'step': 'form_filling',
                            'timestamp': datetime.now().isoformat()
                        }
                    }
                    logging.error(f"❌ Automação simulada falhou para visitante {visitor_id}")
            
        except Exception as e:
            logging.error(f"❌ Erro durante automação simulada para visitante {visitor_id}: {e}")
            
            with automation_lock:
                automation_status[visitor_id] = {
                    'status': 'failed',
                    'started_at': automation_status[visitor_id]['started_at'],
                    'completed_at': datetime.now().isoformat(),
                    'step': 'error',
                    'message': f'Erro durante automação: {str(e)}',
                    'result': {'success': False, 'error': str(e)}
                }
        
        finally:
            # Limpar estado
            self.is_running = False
            self.current_visitor_id = None
    
    def get_status(self, visitor_id):
        """Retorna o status de uma automação"""
        with automation_lock:
            return automation_status.get(visitor_id, None)

# Instância global do gerenciador
automation_manager = MockAutomationManager()

def require_api_key(f):
    """Decorator para verificar API key"""
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'error': 'API key não fornecida'}), 401
        
        api_key = auth_header.split(' ')[1]
        if api_key != API_KEY:
            return jsonify({'error': 'API key inválida'}), 401
        
        return f(*args, **kwargs)
    return decorated_function

@app.route('/api/health', methods=['GET'])
def health_check():
    """Verifica a saúde da API"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'automation_running': automation_manager.is_running,
        'current_visitor': automation_manager.current_visitor_id,
        'message': 'Servidor de teste funcionando!'
    })

@app.route('/api/hikcentral/automation', methods=['POST'])
@require_api_key
def start_automation():
    """Inicia uma nova automação"""
    try:
        data = request.get_json()
        
        if not data or 'visitor_id' not in data or 'visitor_data' not in data:
            return jsonify({
                'success': False,
                'error': 'visitor_id e visitor_data são obrigatórios'
            }), 400
        
        visitor_id = data['visitor_id']
        visitor_data = data['visitor_data']
        
        # Validar dados obrigatórios
        required_fields = ['name', 'cpf', 'phone']
        for field in required_fields:
            if field not in visitor_data:
                return jsonify({
                    'success': False,
                    'error': f'Campo obrigatório ausente: {field}'
                }), 400
        
        logging.info(f"🚀 Recebida solicitação de automação para visitante {visitor_id}")
        
        # Iniciar automação
        success, message = automation_manager.start_automation(visitor_id, visitor_data)
        
        if success:
            return jsonify({
                'success': True,
                'message': message,
                'visitor_id': visitor_id,
                'timestamp': datetime.now().isoformat()
            })
        else:
            return jsonify({
                'success': False,
                'error': message,
                'visitor_id': visitor_id,
                'timestamp': datetime.now().isoformat()
            }), 400
            
    except Exception as e:
        logging.error(f"Erro ao iniciar automação: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@app.route('/api/hikcentral/status/<visitor_id>', methods=['GET'])
@require_api_key
def get_automation_status(visitor_id):
    """Retorna o status de uma automação"""
    try:
        status = automation_manager.get_status(visitor_id)
        
        if not status:
            return jsonify({
                'success': False,
                'error': 'Visitante não encontrado',
                'visitor_id': visitor_id
            }), 404
        
        return jsonify({
            'success': True,
            'visitor_id': visitor_id,
            'status': status,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logging.error(f"Erro ao buscar status: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@app.route('/api/hikcentral/automations', methods=['GET'])
@require_api_key
def list_automations():
    """Lista todas as automações"""
    try:
        with automation_lock:
            return jsonify({
                'success': True,
                'automations': automation_status,
                'timestamp': datetime.now().isoformat()
            })
            
    except Exception as e:
        logging.error(f"Erro ao listar automações: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

if __name__ == '__main__':
    logging.info(f"🚀 Iniciando servidor de teste na porta {PORT}")
    logging.info(f"🔑 API Key: {API_KEY}")
    logging.info("📝 Este é um servidor de SIMULAÇÃO - não executa automação real!")
    
    try:
        app.run(
            host='0.0.0.0',
            port=PORT,
            debug=False,
            threaded=True
        )
    except KeyboardInterrupt:
        logging.info("🛑 Servidor interrompido pelo usuário")
    except Exception as e:
        logging.error(f"❌ Erro ao iniciar servidor: {e}")
        import sys
        sys.exit(1) 