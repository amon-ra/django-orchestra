Installation
============

Django-orchestra ships with a set of management commands for automating some of the installation steps.

These commands are meant to be run within a **clean** Debian-like distribution, you should be specially careful while following this guide on a customized system.

Django-orchestra can be installed on any Linux system, however it is **strongly recommended** to chose the reference platform for your deployment (Debian 8.0 jessie and Python 3.4).


1. Create a system user for running Orchestra
    ```bash
    adduser orchestra
    # not required but it will be very handy
    sudo adduser orchestra sudo
    su - orchestra
    ```

2. Install django-orchestra's source code
    ```bash
    sudo apt-get install python3-pip
    sudo pip install django-orchestra==dev
    ```

3. Install requirements
    ```bash
    sudo orchestra-admin install_requirements
    ```

4. Create a new project
    ```bash
    cd ~orchestra
    orchestra-admin startproject <project_name> # e.g. panel
    cd <project_name>
    sudo touch /var/log/orchestra.log
    sudo chown orchestra /var/log/orchestra.log
    ```

5. Create and configure a Postgres database
    ```bash
    sudo python3 manage.py setuppostgres --db_password <password>
    # admin_tools needs accounts and does not have migrations
    python3 manage.py migrate accounts
    python3 manage.py migrate
    ```

7. Configure celeryd
    ```bash
    sudo python3 manage.py setupcelery --username orchestra
    ```

8. Configure the web server:
    ```bash
    python3 manage.py collectstatic --noinput
    sudo apt-get install nginx-full uwsgi uwsgi-plugin-python3
    sudo python3 manage.py setupnginx
    ```

9. Start all services:
    ```bash
    sudo python manage.py startservices
    ```


Upgrade
=======
To upgrade your Orchestra installation to the last release you can use `upgradeorchestra` management command. Before rolling the upgrade it is strongly recommended to check the [release notes](http://django-orchestra.readthedocs.org/en/latest/).
```bash
sudo python3 manage.py upgradeorchestra
```

Current in *development* version (master branch) can be installed by
```bash
sudo python3 manage.py upgradeorchestra dev
```

Additionally the following command can be used in order to determine the currently installed version:
```bash
python3 manage.py orchestraversion
```



Extra
=====

1. Generate a passwordless ssh key for orchestra user
ssh-keygen

2. Copy this key to all servers orchestra will manage, including itself is neccessary
ssh-copy-id root@<server-address>

