# İçeri Aktarma
from flask import Flask, render_template,request, redirect, jsonify
# Veritabanı kütüphanesini içe aktarma
from flask_sqlalchemy import SQLAlchemy
# Ses tanıma kütüphanesini içe aktarma
import speech_recognition as sr
import io
import base64
import wave
import tempfile
import os
from pydub import AudioSegment
import random
import time


app = Flask(__name__)
# SQLite ile bağlantı kurma 
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///diary.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
# DB oluşturma
db = SQLAlchemy(app )

# Oyun seviyeleri
GAME_LEVELS = {
    "kolay": ["dairy", "mouse", "computer", "phone", "book", "table", "chair", "house", "car", "tree"],
    "orta": ["programming", "algorithm", "developer", "database", "software", "hardware", "network", "security", "interface", "application"],
    "zor": ["neural network", "machine learning", "artificial intelligence", "data structure", "object oriented", "web development", "cloud computing", "cyber security", "user experience", "application programming"]
}

#Görev #1. DB tablosu oluşturma
class Card(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    subtitle = db.Column(db.String(100), nullable=False)
    text = db.Column(db.String, nullable=False)
    
    def __repr__(self):
        return f'<Card {self.id}>'











# İçerik sayfasını çalıştırma
@app.route('/')
def index():
    # DB nesnelerini görüntüleme
    # Görev #2. DB'deki nesneleri index.html'de görüntüleme
    cards = Card.query.order_by(Card.id).all()

    return render_template('index.html',
                           cards=cards
                           )

# Kartla sayfayı çalıştırma
@app.route('/card/<int:id>')
def card(id):
    # Görev #2. Id'ye göre doğru kartı görüntüleme
    card = Card.query.get_or_404(id)

    return render_template('card.html', card=card)

# Sayfayı çalıştırma ve kart oluşturma
@app.route('/create')
def create():
    return render_template('create_card.html')

# Kart formu
@app.route('/form_create', methods=['GET','POST'])
def form_create():
    if request.method == 'POST':
        title =  request.form['title']
        subtitle =  request.form['subtitle']
        text =  request.form['text']

        # Görev #2. Verileri DB'de depolamak için bir yol oluşturma
        card = Card(title=title, subtitle=subtitle, text=text)
        db.session.add(card)
        db.session.commit()

        return redirect('/')
    else:
        return render_template('create_card.html')

# Ses tanıma endpoint'i
@app.route('/speech_to_text', methods=['POST'])
def speech_to_text():
    try:
        # Ses dosyasını al
        audio_data = request.files['audio']
        
        # Geçici dosyalar oluştur
        with tempfile.NamedTemporaryFile(delete=False, suffix='.webm') as temp_webm:
            with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as temp_wav:
                # Ses verisini geçici dosyaya kaydet
                audio_data.save(temp_webm.name)
                temp_webm_path = temp_webm.name
                temp_wav_path = temp_wav.name
        
        try:
            # WebM dosyasını WAV formatına dönüştür
            audio = AudioSegment.from_file(temp_webm_path)
            audio = audio.set_frame_rate(16000)  # 16kHz'e düşür
            audio = audio.set_channels(1)  # Mono yap
            audio.export(temp_wav_path, format="wav")
            
            # SpeechRecognition nesnesi oluştur
            recognizer = sr.Recognizer()
            
            # Ses dosyasını oku
            with sr.AudioFile(temp_wav_path) as source:
                # Gürültü azaltma
                recognizer.adjust_for_ambient_noise(source, duration=0.5)
                audio = recognizer.record(source)
            
            # Google Web Speech API ile tanıma yap
            text = recognizer.recognize_google(audio, language='tr-TR')
            
            return jsonify({'success': True, 'text': text})
            
        finally:
            # Geçici dosyaları sil
            for temp_path in [temp_webm_path, temp_wav_path]:
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
    
    except sr.UnknownValueError:
        return jsonify({'success': False, 'error': 'Ses anlaşılamadı. Lütfen daha net konuşun.'})
    except sr.RequestError as e:
        return jsonify({'success': False, 'error': f'API hatası: {str(e)}'})
    except Exception as e:
        return jsonify({'success': False, 'error': f'Beklenmeyen hata: {str(e)}'})

# Oyun sayfası
@app.route('/game')
def game():
    return render_template('game.html', levels=GAME_LEVELS.keys())

# Oyun başlatma
@app.route('/start_game', methods=['POST'])
def start_game():
    level = request.json.get('level', 'kolay')
    if level not in GAME_LEVELS:
        return jsonify({'success': False, 'error': 'Geçersiz seviye'})
    
    # Rastgele kelime seç
    word = random.choice(GAME_LEVELS[level])
    
    return jsonify({
        'success': True, 
        'word': word,
        'level': level,
        'max_attempts': 3,
        'time_limit': 10
    })

# Oyun kelime kontrolü
@app.route('/check_word', methods=['POST'])
def check_word():
    try:
        # Ses dosyasını al
        audio_data = request.files['audio']
        target_word = request.form.get('target_word', '').lower()
        
        # Geçici dosyalar oluştur
        with tempfile.NamedTemporaryFile(delete=False, suffix='.webm') as temp_webm:
            with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as temp_wav:
                # Ses verisini geçici dosyaya kaydet
                audio_data.save(temp_webm.name)
                temp_webm_path = temp_webm.name
                temp_wav_path = temp_wav.name
        
        try:
            # WebM dosyasını WAV formatına dönüştür
            audio = AudioSegment.from_file(temp_webm_path)
            audio = audio.set_frame_rate(16000)
            audio = audio.set_channels(1)
            audio.export(temp_wav_path, format="wav")
            
            # SpeechRecognition nesnesi oluştur
            recognizer = sr.Recognizer()
            
            # Ses dosyasını oku
            with sr.AudioFile(temp_wav_path) as source:
                recognizer.adjust_for_ambient_noise(source, duration=0.5)
                audio = recognizer.record(source)
            
            # Google Web Speech API ile tanıma yap (İngilizce)
            recognized_text = recognizer.recognize_google(audio, language="en-GB").lower()
            
            # Kelime kontrolü
            is_correct = target_word in recognized_text or recognized_text in target_word
            
            return jsonify({
                'success': True, 
                'recognized': recognized_text,
                'target': target_word,
                'correct': is_correct
            })
            
        finally:
            # Geçici dosyaları sil
            for temp_path in [temp_webm_path, temp_wav_path]:
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
    
    except sr.UnknownValueError:
        return jsonify({'success': False, 'error': 'Ses anlaşılamadı. Lütfen daha net konuşun.'})
    except sr.RequestError as e:
        return jsonify({'success': False, 'error': f'API hatası: {str(e)}'})
    except Exception as e:
        return jsonify({'success': False, 'error': f'Beklenmeyen hata: {str(e)}'})


if __name__ == "__main__":
    app.run(debug=True)
