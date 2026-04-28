#!/bin/bash
# 인스턴스 A → 인스턴스 B 서버 이전 스크립트
# 실행 위치: 인스턴스 A
# 사용법: bash migrate_db.sh <B_IP> <B_PEM_PATH>
set -e

B_IP=$1
B_PEM=$2

if [ -z "$B_IP" ] || [ -z "$B_PEM" ]; then
  echo "사용법: bash migrate_db.sh <B_IP> <B_PEM_PATH>"
  exit 1
fi

DB_NAME=seconddeal
DB_USER=root
DUMP_FILE=/tmp/seconddeal_$(date +%Y%m%d_%H%M%S).sql

echo "== [1/5] DB 스냅샷 추출 (mysqldump) =="
mysqldump -u $DB_USER -p $DB_NAME > $DUMP_FILE
echo "덤프 완료: $DUMP_FILE"

echo "== [2/5] 덤프 파일을 인스턴스 B로 전송 =="
scp -i $B_PEM $DUMP_FILE ubuntu@$B_IP:/tmp/

echo "== [3/5] 인스턴스 B에서 DB 복원 =="
ssh -i $B_PEM ubuntu@$B_IP << REMOTE
  mysql -u root -p -e "CREATE DATABASE IF NOT EXISTS $DB_NAME CHARACTER SET utf8mb4;"
  mysql -u root -p $DB_NAME < /tmp/$(basename $DUMP_FILE)
  echo "DB 복원 완료"
REMOTE

echo "== [4/5] 인스턴스 B에 코드 배포 =="
ssh -i $B_PEM ubuntu@$B_IP << REMOTE
  if [ -d ~/seconddeal ]; then
    cd ~/seconddeal && git pull origin main
  else
    git clone https://github.com/philocsera/toy_proj_seconddeal.git ~/seconddeal
  fi
  cd ~/seconddeal
  source venv/bin/activate
  pip install -r requirements.txt gunicorn mysqlclient
  python manage.py migrate
  python manage.py collectstatic --noinput
  sudo systemctl restart seconddeal
REMOTE

echo "== [5/5] Nginx upstream을 인스턴스 B로 전환 =="
# 현재 A의 Nginx upstream을 B IP로 변경
sudo sed -i "s/127.0.0.1:8000/$B_IP:8000/" /etc/nginx/sites-available/seconddeal
sudo nginx -t && sudo systemctl reload nginx

echo "== 서버 이전 완료. 트래픽이 인스턴스 B로 전환됨 =="
echo "다운타임: 약 0초 (Nginx reload는 무중단)"
