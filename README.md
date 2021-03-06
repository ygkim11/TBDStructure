# TDB Structure

## 자동매매툴 (실제/백테스팅 매매 지원)

키움, 이베스트, 바이낸스 등 API를 활용하여 실제 매매와 백테스팅을 진행할 수 있는 프로그램


### 용어 설명:

TBD툴은 큐를 활용하여 여러 프로세스 사이의 소통을 관리한다.

1. data_queue: data queue를 통해서 Strategy, Portfolio는 마켓 이벤트를 전송 받는다.

2. port_queue: port_queue는 여러 클래스로부터 이벤트를 받아 각 이벤트에 맞게 처리한다.
               모든 이벤트는 결국 실제 매매나 포트폴리오 정보의 업데이트가 필요하기 때문에 필요하다.

3. api_queue: api_queue는 API와 DataHandler의 연결을 해준다. API(키움, 이베스트, 바이낸스)에서 발생하는 실시간 데이터를
              DataHandler로 보내어주어 shared_memory를 만들게 해주기 위함이다.

4. order_queue: 키움과 같은 툴은 한 계정으로 하나의 프로그램(창)밖에 사용하지 못하기 때문에
                Portfolio/Execution에서 보내오는 order 이벤트를 order_queue에서 받아서 처리해준다.
   

추가로, shared_memory는 DataHandler에서 만들고 그 정보를 Strategy로 보내 주어:

- self.tick_mem_array
- self.hoga_mem_array
- self.min_mem_array

로 사용할 수 있도록 해준다.


### DB 사용방법:

데이터베이스는 Django 웹프레임워크에서 사용하는 model을 사용한다.  
이의 장점으로:

- 거대 커뮤니티가 뒤에 존재한다는 점
- 다른 데이터베이스에서도 같은 방식으로 쿼리를 사용할 수 있다는 점
- 최적화 작업이 쉽게 된다는 점
- 사용이 상당히 쉽다는 점
- 그리고 웹에서도 쉽게 연동할 수 있다는 점

이 있다.

Django 관련 폴더는 모두: api, core이다.  
api가 메인 프로젝트명이며 폴더내 settings.py 파일을 보면 config 사항들을 확인할 수 있다.  
core는 코어 앱을 정의내린 부분이다. 모델 정의, api endpoint 정의 등을 한 곳이다.

Django model(DB)을 사용하기 위해서는:

```bash
pip install -r requirements.txt
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser
```

을 차례로 실행한 다음 유저를 생성한 다음 사용할 수 있다.  
makemigrations, migrate를 하면 core/models에서 정의된 모든 테이블을 db.sqlite3에 생성해준다.

Django 프로젝트 외 다른 파일에서도 Django 관련 DB를 사용할 수 있도록 db.py 파일에 Django model wrapper 클래스를 정의하였다.  
Django 모델 언어는 Django 내부에서만 사용되지만,

```python
import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "api.settings")
application = get_wsgi_application()
```

와 같이 해주면 Django 관련 setting 내용을 파일로 import하여 사용할 수 있게 된다.

하지만, 직접 이렇게 Django setting을 import하는 것보다 DB 관련 작업은 모두 db.py에 정의하여 사용하도록 한다.  

추가로, Django 모델을 쉘로 디버깅하고 싶을 때는 일반 터미널로는 안 되고 Django에서 제공하는 shell을 사용하는게 편리하다.  

```bash
python manage.py shell
```

을 실행하면 Django settings가 import된 쉘을 실행해준다. 그렇게 하였다면:

```python
from core.models import OHLCV

price_data = OHLCV.objects.filter(code='005930').all()
```

과 같은 Django 관련 스크립트를 사용할 수 있게 된다.  

Reference: <https://docs.djangoproject.com/en/3.1/topics/db/models/>