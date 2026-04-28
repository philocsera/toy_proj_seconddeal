#!/bin/bash
# EC2 인스턴스 A 초기 배포 스크립트
# 실행: bash deploy.sh
set -e

PROJECT_DIR=/home/ubuntu/seconddeal
VENV=$PROJECT_DIR/venv

echo "== [1/6] 패키지 업데이트 =="
sudo apt-get update -y && sudo apt-get upgrade -y
sudo apt-get install -y python3-pip python3-venv nginx mysql-server libmysqlclient-dev

echo "== [2/6] 프로젝트 클론 =="
cd /home/ubuntu
git clone https://github.com/philocsera/toy_proj_seconddeal.git seconddeal
cd $PROJECT_DIR

echo "== [3/6] 가상환경 & 의존성 설치 =="
python3 -m venv venv
source $VENV/bin/activate
pip install -r requirements.txt gunicorn mysqlclient

echo "== [4/6] .env 설정 (사전에 업로드 필요) =="
# scp .env ubuntu@<EC2_IP>:~/seconddeal/.env 로 미리 업로드
if [ ! -f .env ]; then
  echo ".env 파일이 없습니다. 업로드 후 재실행하세요." && exit 1
fi

echo "== [5/6] DB 마이그레이션 & 정적 파일 수집 =="
source $VENV/bin/activate
python manage.py migrate
python manage.py collectstatic --noinput

echo "== [6/6] Nginx & Gunicorn 서비스 등록 =="
sudo mkdir -p /var/log/gunicorn
sudo chown ubuntu:ubuntu /var/log/gunicorn

sudo cp $PROJECT_DIR/deploy/gunicorn.service /etc/systemd/system/seconddeal.service
sudo systemctl daemon-reload
sudo systemctl enable seconddeal
sudo systemctl start seconddeal

sudo cp $PROJECT_DIR/deploy/nginx.conf /etc/nginx/sites-available/seconddeal
sudo ln -sf /etc/nginx/sites-available/seconddeal /etc/nginx/sites-enabled/seconddeal
sudo nginx -t && sudo systemctl reload nginx

echo "== 배포 완료 =="
