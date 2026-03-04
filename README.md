\# FocusSpace - 會議室預約小工具

這是我用 Python Flask 練習寫的一個會議室預約系統。





\## 主要功能



* 日曆看板介面：整合 FullCalendar.js，提供週視圖與日視圖，方便查看時段佔用情況。
* 快速預約機制：使用者可直接點擊日曆上的空白時段，系統會自動將日期與時間填入預約表單。
* 預約衝突比對：後端程式會檢查時間區間，若與現有紀錄重疊則無法預約。
* 時長與時效管理：單次預約上限為 4 小時，系統會自動在列表隱藏已過期的預約紀錄。
* Email 通知系統：預約完成後，系統會自動發送電子郵件至使用者信箱作為證明。
* 權限管理：區分一般使用者與管理員，管理員可進入後台管理帳號與預約資料。



\##  用到的技術

* 後端：Python / Flask
* 資料庫：SQLite 3 (手寫 SQL 語法，不使用 ORM 套件)
* 前端：HTML / Bootstrap 5 / FullCalendar / Vanilla JavaScript
* 安全性：Werkzeug 密碼加密 / .env 環境變數管理



\##  如何在你的電腦上跑起來



如果你想試用看看，請跟著以下步驟：



1\. \*\*下載專案\*\*

git clone https://github.com/你的帳號/FocusSpace-Booking-System.git

cd FocusSpace-Booking-System



2. \*\*環境準備\*

python -m venv venv

.\\venv\\Scripts\\activate

pip install flask flask-mail python-dotenv werkzeug



3. \*\*設定 Email\*\* 因為有寄信功能，請打開 app.py，找到設定 Email 的地方，填入你自己的 Gmail 帳號跟應用程式密碼：

app.config\['MAIL\_USERNAME'] = '你的Gmail帳號'

app.config\['MAIL\_PASSWORD'] = '你的應用程式密碼'



4\. \*\*執行\*\*

python app.py



看到跑出網址後，打開瀏覽器輸入 http://127.0.0.1:5000 就可以用了

