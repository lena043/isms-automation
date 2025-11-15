

### 동작 방법

- Secrets : dev/isms
- GoogleSheeet 위치 : ISMS_Automation 문서 (dev/isms 안에 google key 로 설정)
```export ISMS_SECRET_NAME='dev/isms' && aws-vault exec socar-sso-dev -- .venv/bin/python main.py```