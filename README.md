\# FocusSpace - 會議室預約小工具 



這是我用 Python Flask 練習寫的一個會議室預約系統。

主要目的是解決公設空間預約使用的問題。系統很簡單，但該有的防呆功能都有。



\## 主要功能



\- 看誰預約：首頁直接列出所有預約紀錄，哪個時段被誰訂走，一目了然。

\- 防撞期機制：如果你選的時間已經有人訂了（哪怕只重疊一分鐘），系統會擋住你，不讓你預約。

\- Email 通知：預約成功後，系統會自動寄一封信到你的信箱，當作預約證明。

\- 分身分登入：

  - 一般人：只能預約。

  - 管理員：可以登入後台，把別人亂訂的或是測試用的預約刪掉。



\##  用到的技術



這個專案雖然不大，但我練習了開發的完整流程：

\- 後端：Python (Flask) - 處理網頁邏輯。

\- 資料庫：SQLite - 為了練習 SQL 邏輯，我沒有用套件，而是直接寫 SQL 語法來抓取和比對資料。

\- 前端：HTML + Bootstrap 5 - 簡單乾淨的排版。

\- 版控：Git \& GitHub。



\##  如何在你的電腦上跑起來



如果你想試用看看，請跟著以下步驟：



1\. \*\*下載專案\*\*

   ```bash

   git clone \[https://github.com/HsinmeiCho/FocusSpace-Booking-System.git](https://github.com/HsinmeiCho/FocusSpace-Booking-System.git)

   cd FocusSpace-Booking-System



2. \*\*安裝所需檔案\*\*

pip install flask flask-mail werkzeug



3. \*\*設定 Email\*\* 因為有寄信功能，請打開 app.py，找到設定 Email 的地方，填入你自己的 Gmail 帳號跟應用程式密碼：

app.config\['MAIL\_USERNAME'] = '你的Gmail帳號'

app.config\['MAIL\_PASSWORD'] = '你的應用程式密碼'



4\. \*\*執行\*\*

python app.py



看到跑出網址後，打開瀏覽器輸入 http://127.0.0.1:5000 就可以用了

