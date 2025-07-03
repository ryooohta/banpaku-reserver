from flask import Flask, request, render_template_string, session, redirect, url_for
import requests
import time
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'Banpakuwakuwaku333'

PASSWORD = "Banpakuwakuwaku333"

LOGIN_HTML = '''
<!doctype html>
<title>ログイン</title>
<h1>ログインしてください</h1>
<form method="POST">
  <label>パスワード: <input type="password" name="password" required></label>
  <input type="submit" value="ログイン">
</form>
{% if error %}<p style="color:red">{{ error }}</p>{% endif %}
'''

RESERVATION_HTML = '''
<!doctype html>
<title>万博予約ツール1.1</title>
<h1>万博予約ツール</h1>
<form method="POST">
  <h2>共通情報</h2>
  <label>クッキー<br><textarea name="cookie" rows="3" cols="80" required>{{ cookie }}</textarea></label><br><br>
  <label>チケットID（カンマ区切り）<br><input type="text" name="ticket_ids" value="{{ ticket_ids }}" required></label><br><br>
  <label>入場日（例: 2025-06-30）<br><input type="date" name="entry_date" value="{{ entry_date }}" required></label><br><br>
  <label>最大リクエスト回数<br><input type="number" name="max_requests" value="{{ max_requests }}" min="1" required></label><br><br>
  <label>リクエスト間隔（秒）<br><input type="number" step="0.1" name="interval_sec" value="{{ interval_sec }}" min="0" required></label><br><br>

  <hr>
  <h2>通常入場予約</h2>
  <input type="hidden" name="form_type" value="entry">
  <label>入場時間<br>
    <select name="entry_time">
      <option value="0700" {% if entry_time == "0700" %}selected{% endif %}>09:00</option>
      <option value="0900" {% if entry_time == "0900" %}selected{% endif %}>10:00</option>
      <option value="1000" {% if entry_time == "1000" %}selected{% endif %}>11:00</option>
      <option value="1100" {% if entry_time == "1100" %}selected{% endif %}>12:00</option>
    </select>
  </label><br><br>
  <label>ゲート選択<br>
    <select name="gate">
      <option value="1" {% if gate == "1" %}selected{% endif %}>東ゲート</option>
      <option value="2" {% if gate == "2" %}selected{% endif %}>西ゲート</option>
    </select>
  </label><br><br>
  <input type="submit" name="entry_submit" value="入場予約開始">
</form>

<form method="POST">
  <hr>
  <h2>パビリオン予約</h2>
  <input type="hidden" name="form_type" value="pavilion">
  <input type="hidden" name="cookie" value="{{ cookie }}">
  <input type="hidden" name="ticket_ids" value="{{ ticket_ids }}">
  <input type="hidden" name="entry_date" value="{{ entry_date }}">
  <input type="hidden" name="max_requests" value="{{ max_requests }}">
  <input type="hidden" name="interval_sec" value="{{ interval_sec }}">
  <label>予約時間（4桁: 1900など）<br><input type="text" name="start_time" required></label><br><br>
  <label>イベントコード（例: C730）<br><input type="text" name="event_code" required></label><br><br>
  <input type="submit" name="pavilion_submit" value="パビリオン予約開始">
</form>

<hr>
<h2>実行ログ</h2>
<pre style="white-space: pre-wrap">{{ message }}</pre>
'''

def send_entry_reservation(cookie, ticket_ids, entry_date, entry_time, gate):
    url = 'https://ticket.expo2025.or.jp/api/d/user_visiting_reservations'
    headers = {'Content-Type': 'application/json', 'Cookie': cookie.strip(), 'User-Agent': 'Mozilla/5.0'}
    data = {
        "ticket_ids": ticket_ids,
        "start_time": entry_time,
        "gate_type": gate,
        "entrance_date": entry_date.replace('-', '')
    }
    try:
        res = requests.post(url, json=data, headers=headers, timeout=10)
        if res.status_code == 200 and res.json().get('user_visiting_reservation_ids'):
            return True, f"✅ 入場予約成功: {ticket_ids} → {res.json()['user_visiting_reservation_ids']}"
        return False, f"❌ 入場予約失敗: {res.text}"
    except Exception as e:
        return False, f"❌ 入場予約エラー: {str(e)}"

def send_pavilion_reservation(cookie, ticket_ids, entry_date, start_time, event_code):
    url = 'https://ticket.expo2025.or.jp/api/d/user_event_reservations'
    headers = {'Content-Type': 'application/json', 'Cookie': cookie.strip(), 'User-Agent': 'Mozilla/5.0'}
    data = {
        "ticket_ids": ticket_ids,
        "entrance_date": entry_date.replace('-', ''),
        "start_time": start_time,
        "event_code": event_code,
        "registered_channel": "5"
    }
    try:
        res = requests.post(url, json=data, headers=headers, timeout=10)
        if res.status_code == 200 and res.json().get('user_event_reservation_ids'):
            return True, f"✅ パビリオン予約成功: {ticket_ids} → {res.json()['user_event_reservation_ids']}"
        return False, f"❌ パビリオン予約失敗: {res.text}"
    except Exception as e:
        return False, f"❌ パビリオン予約エラー: {str(e)}"

@app.route('/', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        if request.form['password'] == PASSWORD:
            session['logged_in'] = True
            return redirect(url_for('index'))
        else:
            error = "パスワードが間違っています"
    return render_template_string(LOGIN_HTML, error=error)

@app.route('/app', methods=['GET', 'POST'])
def index():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    message = ''
    cookie = request.form.get('cookie', '')
    ticket_ids_raw = request.form.get('ticket_ids', '')
    entry_date = request.form.get('entry_date', '')
    entry_time = request.form.get('entry_time', '0700')
    gate = request.form.get('gate', '1')
    max_requests = int(request.form.get('max_requests', 100))
    interval_sec = float(request.form.get('interval_sec', 1.0))
    start_time = request.form.get('start_time', '')
    event_code = request.form.get('event_code', '')

    if request.method == 'POST':
        form_type = request.form.get('form_type')
        ticket_ids = [tid.strip() for tid in ticket_ids_raw.split(',') if tid.strip()]
        logs = []
        success = False

        for i in range(1, max_requests + 1):
            if form_type == 'entry':
                ok, result = send_entry_reservation(cookie, ticket_ids, entry_date, entry_time, gate)
            elif form_type == 'pavilion':
                ok, result = send_pavilion_reservation(cookie, ticket_ids, entry_date, start_time, event_code)
            else:
                ok, result = False, "❌ フォームタイプが不明です"
            logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] {result}")
            if ok:
                success = True
                logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] ✅ 成功したため停止します。")
                break
            logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] リクエスト {i} 終了。次を待機中...")
            time.sleep(interval_sec)

        if not success:
            logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] ❌ 予約成功しませんでした。")

        message = '\n'.join(logs)

    return render_template_string(RESERVATION_HTML, message=message, cookie=cookie, ticket_ids=ticket_ids_raw,
                                  entry_date=entry_date, entry_time=entry_time, gate=gate,
                                  max_requests=max_requests, interval_sec=interval_sec)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3000)
      
