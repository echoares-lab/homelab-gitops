#!/bin/sh
# ====================================
#  Release Date : 2023-02-07
#  Version      : 1.1.0
#  Platform     : x86_64
# ====================================
MODEL="EPC"
VERSION="1.9.0"
RELEASE_DATE="2026-06-03"
ENVIRONMENT=0

ROOT_PATH=${PWD}
TMP_PATH="/tmp"
EPC_LOG_PATH="/var/log/epc"
EPC_PATH="/epc"
INI_FILE="${EPC_PATH}/config.ini"
CERT_DIR=${EPC_PATH}"/portal_cert/"
EPC_PIPE_PATH=${EPC_PATH}"/pipe"
WATCHDOG="${EPC_PIPE_PATH}/fitdog"
EPC_PIPE_MSG=${EPC_PIPE_PATH}"/msg"
EPC_PIPE_REQ=${EPC_PIPE_PATH}"/req"
ENV_FILE=${EPC_PIPE_PATH}"/.epc-prod"
EPC_PIPE_HOST=${EPC_PIPE_PATH}"/host"
HOST_LISTENER="${EPC_PIPE_PATH}/host.sh"
REPO="public.ecr.aws/d3g4m7o9/"
S3_URL="http://engenius-epc.s3.us-west-2.amazonaws.com/dev/"
#LATEST_VERSION=$(curl -s "http://ocu-sqa.engeniuscloud.com/epc/version?stage=1&os=0" | tail -1)

#docker-compose-staging.yml for testing, docker-compose.yml for release production
#EPC_YML="docker-compose-staging.yml"
EPC_YML="docker-compose.yml"
DOCKER_COMPOSE_CMD="docker-compose -p epc -f $EPC_PIPE_PATH/${EPC_YML} --env-file $ENV_FILE"
INIT_TIMEOUT=60
keep_license=1 #0:remove license, 1:keep license

# Agent settings
AGENT_YML="agent.yml"
AGENT_ENV="${EPC_PIPE_PATH}/.agent"
AGENT_CMD="docker-compose -p agent -f $EPC_PIPE_PATH/${AGENT_YML} --env-file $AGENT_ENV"
IP_ADDR=$(ip r | awk 'NR==2' | awk -F" " '{print $NF}')
GREEN="\033[0;32m"
NC="\033[0m"

inspect(){
    #check whether curl is existed, if not then install curl
    if [ -z $(which curl) ]; then su -c "apt-get update && apt-get install curl"; fi

    #LATEST_VERSION=$(curl -s "http://ocu-sqa.engeniuscloud.com/epcpro/version?stage=1&os=0" | tail -1)
    LATEST_VERSION="1.9.0"
    if [ "$LATEST_VERSION" = "0" ]; then
        echo "[ERROR] Can not get new $MODEL version."
        exit 1
    fi
}

info(){
    echo "[$MODEL]"
    echo "Version: $VERSION"
    echo "Release date: $RELEASE_DATE"
}

install(){
    if [ ! -z "$1" ]; then LATEST_VERSION=$1; fi
    if [ -z "$LATEST_VERSION" ]; then echo "[ERROR] Need to install later because latest version can not get." && exit 1; fi
    echo "Install $MODEL version: ${LATEST_VERSION}"
    if [ $ENVIRONMENT -eq 0 ]; then install_tools; fi
    if [ ! check_ports ]; then exit 1; fi
    if [ ! -d $EPC_PATH ]; then keep_license=0; fi
    create_folders
    download_inst_files
    download_cert
    setup_env
    if [ $ENVIRONMENT -eq 0 ]; then pull_docker_images; fi
    start
    create_uuid
    db_init
    start_otter
    echo "$MODEL installation was successful."
}

install_tools(){
    if [ -z $(which sudo) ]; then
        echo "Using apt-get install sudo"
        su -c "apt-get update && apt-get install sudo && sudo adduser $USER sudo && /sbin/reboot"
    fi

    if [ $(id -u) -ne 0 ]; then echo "Permission denied, please run as sudo."; fi
    if [ -z $(which wget) ]; then su -c "apt-get install wget"; fi
    if [ -z $(which netstat) ]; then su -c "apt-get install net-tools"; fi

    TARGET_DOCKER_VERSION="27.1.2"
    TARGET_COMPOSE_VERSION="v2.29.2"
    # Compare two version:
    # Arguments:
    #     $1: Current Version (v1)
    #     $2: Target Version (v2)
    # Return:
    #     0: v1 == v2
    #     1: v1 > v2
    #     2: v1 < v2
    compare_version() {
        if [ "$1" = "$2" ]; then return 0; fi
        local sorted=$(printf '%s\n%s' "$1" "$2" | sort -V | head -n1)
        if [ "$sorted" = "$1" ]; then
            return 2
        else
            return 1
        fi 
    }

    install_docker_engine() {
        local VERSION=$1
        OS=$(lsb_release -si | tr '[:upper:]' '[:lower:]')
        curl -fsSL https://download.docker.com/linux/$OS/gpg | sudo gpg --batch --yes --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
        echo "deb [arch=amd64 signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/$OS $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
        apt-get update
        VERSION_STR=$(apt-cache madison docker-ce | grep "$TARGET_DOCKER_VERSION" | head -1 | awk '{print $3}')
        if [ -z "$VERSION_STR" ]; then
            echo "Docker ${TARGET_DOCKER_VERSION} not found in repository, installing latest available version."
            apt-get install -y docker-ce docker-ce-cli containerd.io
        else
            apt-get install -y docker-ce=$VERSION_STR docker-ce-cli=$VERSION_STR containerd.io
        fi
    }

    install_docker_compose() {
        local VERSION=$1
        sudo curl -L "https://github.com/docker/compose/releases/download/${TARGET_COMPOSE_VERSION}/docker-compose-$(uname -s | tr '[:upper:]' '[:lower:]')-$(uname -m)" -o /usr/local/bin/docker-compose
        sudo chmod +x /usr/local/bin/docker-compose
        sudo mkdir -p /usr/local/lib/docker/cli-plugins
        sudo ln -sf /usr/local/bin/docker-compose /usr/local/lib/docker/cli-plugins/docker-compose
    }
        
    # check current docker version & install docker engine
    CURRENT_DOCKER_VERSION=$(docker version --format '{{.Server.Version}}' 2>/dev/null)
    if [ -z "$CURRENT_DOCKER_VERSION" ]; then
        echo "Installing Docker Engine to ${TARGET_DOCKER_VERSION}..."
        apt-get update
        apt-get install -y apt-transport-https ca-certificates curl gnupg lsb-release
        install_docker_engine "$TARGET_DOCKER_VERSION"
    else
        compare_version "$CURRENT_DOCKER_VERSION" "$TARGET_DOCKER_VERSION"
        RESULT=$?
        if [ $RESULT -eq 2 ]; then
            echo "The minimum Support docker: $TARGET_DOCKER_VERSION (Current Version: $CURRENT_DOCKER_VERSION) Must be updated."
            read -p "Update Docker?[y/n]" choice
            [ "$choice" = "y" ] || [ "$choice" = "Y" ] && install_docker_engine "$TARGET_DOCKER_VERSION" || echo "Skip Update Docker."
        else
            echo "Docker version meets the requirements."
        fi
    fi

    # check current docker compose version & install docker compose
    CURRENT_COMPOSE_VERSION=$(docker-compose version --short 2>/dev/null)
    if [ -z "$CURRENT_COMPOSE_VERSION" ]; then
        CURRENT_COMPOSE_VERSION=$(docker compose version --short 2>/dev/null)
    fi
    if [ -z "$CURRENT_COMPOSE_VERSION" ]; then
        echo "Installing Docker Compose ${TARGET_COMPOSE_VERSION}..."
        install_docker_compose "$TARGET_COMPOSE_VERSION"
    else
        compare_version "${CURRENT_COMPOSE_VERSION#v}" "${TARGET_COMPOSE_VERSION#v}"
        RESULT=$?
        if [ $RESULT -eq 2 ]; then
            echo "The minimum Support Docker Compose: $TARGET_COMPOSE_VERSION (Current Version: $CURRENT_COMPOSE_VERSION) Must be updated."
            read -p "Update Docker-Compose?[y/n]" choice
            if [ "$choice" = "y" ] || [ "$choice" = "Y" ]; then
                install_docker_compose "$TARGET_COMPOSE_VERSION"
            else
                echo "Skip Update Docker Compose."
            fi
        else
            echo "Docker Compose version meets the requirements."
        fi
    fi

    # Ensure docker-compose standalone command is available
    if [ -z "$(which docker-compose 2>/dev/null)" ]; then
        COMPOSE_PLUGIN=$(find /usr/libexec/docker /usr/lib/docker -name 'docker-compose' 2>/dev/null | head -1)
        if [ -n "$COMPOSE_PLUGIN" ]; then
            echo "Creating docker-compose symlink from plugin: $COMPOSE_PLUGIN"
            sudo ln -sf "$COMPOSE_PLUGIN" /usr/local/bin/docker-compose
        fi
    fi
}

check_ports() {
    status=0
    get_ports=$(sudo netstat -tulpn | tail -n +3 | awk {'print $4'} | sed 's/^.*://g' | sort -un)
    open_ports="80 443 8080 18120 1812 1813"

    for open_port in $open_ports
    do
        used=false
        for current_port in $get_ports
        do
            if [ "$open_port" = "$current_port" ]; then
                used=true
                break
            fi
        done
        if [ "$used" = true ] ; then
            status=1
            echo "Port $open_port needs to be allowed."
        fi
    done
    return $status
}

create_folders() {
    if [ ! -d $EPC_PATH ]; then mkdir $EPC_PATH; fi
    if [ ! -d $CERT_DIR ]; then mkdir $CERT_DIR; fi
    if [ ! -d $EPC_LOG_PATH ]; then mkdir $EPC_LOG_PATH; fi
    if [ ! -d $EPC_PIPE_PATH ]; then mkdir $EPC_PIPE_PATH; fi
}

download_inst_files() {
    #wget -q "${S3_URL}epc-inst.tgz" -O "${EPC_PATH}/epc-inst.tgz"
    wget -q "${S3_URL}${LATEST_VERSION}/epc-pkg.tar.gz" -O "${EPC_PATH}/epc-pkg.tar.gz"
    tar zxf "${EPC_PATH}/epc-pkg.tar.gz" -C ${TMP_PATH}
    cp ${TMP_PATH}/epc-pkg/* ${EPC_PIPE_PATH}
    chmod +x ${EPC_PIPE_PATH}/fitdog
    chmod +x ${EPC_PIPE_PATH}/host.sh
    rm -rf "${EPC_PATH}/epc-pkg.tar.gz" "${TMP_PATH}/epc-pkg"
}

update_pkg() {
    wget -q "${S3_URL}${LATEST_VERSION}/epc-pkg.tar.gz" -O "${EPC_PATH}/epc-pkg.tar.gz"
    docker exec -it epc-api sh -c 'tar zxf /epc/epc-pkg.tar.gz -C /tmp'
    docker exec -it epc-api sh -c 'cd /tmp/epc-pkg && ./update.sh'
    rm -rf ${EPC_PATH}/epc-pkg.tar.gz
}

download_cert() {
    # Captive Portal certificate settings
    cert_url="https://s3.us-west-2.amazonaws.com/production.captive-portal.engenius.ai-cert/"
    cert_public="cert.pem"
    cert_private="privkey.pem"
    md5_public="cert_md5.txt"
    md5_private="privkey_md5.txt"
    wget -nv "${cert_url}${cert_public}" -O "${CERT_DIR}${cert_public}" > /dev/null 2>&1
    wget -nv "${cert_url}${cert_private}" -O "${CERT_DIR}${cert_private}" > /dev/null 2>&1
    wget -nv "${cert_url}${md5_public}" -O "${CERT_DIR}${md5_public}" > /dev/null 2>&1
    wget -nv "${cert_url}${md5_private}" -O "${CERT_DIR}${md5_private}" > /dev/null 2>&1
}

setup_env() {
    if [ $keep_license -eq 0 ]; then
        printf "[ocu]\nstage = production\nversion = $LATEST_VERSION" > $INI_FILE
        printf "REPOSITORY_URI=$REPO\nVERSION=$LATEST_VERSION\nHOST_IP=$IP_ADDR\nENABLE=False\nMASTERIP=\nSLAVEIP=" > $ENV_FILE
        printf "REPOSITORY_URI=$REPO\nVERSION=$LATEST_VERSION\nHOST_IP=$IP_ADDR" > $AGENT_ENV
    else
        sed -i '/version =/c\'"version = $LATEST_VERSION" $INI_FILE
        sed -i '/VERSION=/c\'"VERSION=$LATEST_VERSION" $ENV_FILE
        sed -i '/VERSION=/c\'"VERSION=$LATEST_VERSION" $AGENT_ENV
    fi
    if [ $ENVIRONMENT -eq 0 ]; then set_rclocal; fi
}

pull_docker_images() {
    echo "Downloading images..."
    max_retry=6
    interval=20
    for IMAGE in "epc-agent" "epc-api" "epc-db" "epc-raccoon" "epc-otter" "epc-mdns" "epc-radius";
    do
        count=0
        image_name="${REPO}${IMAGE}:${LATEST_VERSION}"
        while [ $count -lt $max_retry ]; do
            docker pull -q "$image_name"
            exit_code=$?
            if [ $exit_code -eq 0 ]; then
                break
            else
                echo "Exit code: $exit_code, retrying for $image_name...($((count+1))/$max_retry)"
                count=$((count + 1))
            fi
            sleep $interval
        done
        if [ $count -ge $max_retry ]; then
            echo "Maximum retry count reached for $image_name, stopping."
            break
        fi
    done
    img_cnt=$(docker images | grep "$LATEST_VERSION" | wc -l)
    if [ ! $img_cnt -eq 7 ]; then
        echo "[ERROR] Pull $MODEL images failed."
        exit 1
    fi
}

pipe_init() {
    # Create named pipes
    if [ ! -p $EPC_PIPE_REQ ]; then mkfifo $EPC_PIPE_REQ; fi
    if [ ! -p $EPC_PIPE_MSG ]; then mkfifo $EPC_PIPE_MSG; fi
    if [ ! -p $EPC_PIPE_HOST ]; then mkfifo $EPC_PIPE_HOST; fi
    # Start host daemon
    if [ -z "$(pgrep fitdog)" ]; then $WATCHDOG & >/dev/null 2>&1; fi
}

check_pipe(){
    rt=$INIT_TIMEOUT
    while [ $rt -ne 0 ]
    do
        if [ ! -z "$(pgrep -f host.sh)" ]; then
            break
        fi
        sleep 1
        rt=$((rt-1))
    done
    if [ $rt -eq 0 ]; then
        echo "Need to init pipe later because $MODEL services can not start."
        exit 1
    fi
}

set_rclocal(){
    if [ ! -f "/etc/rc.local" ]; then
        touch "/etc/rc.local"
        printf "#!/bin/sh -e\n/epc/pipe/fitdog &\nexit 0" > /etc/rc.local
    else
        # check line 2 command
        hostCmd=$(awk 'NR==2' /etc/rc.local)
        if [ "$hostCmd" != "/epc/pipe/fitdog &" ]; then
            awk 'NR==2{printf "/epc/pipe/fitdog &\n"}1' /etc/rc.local > /etc/rc.local_bk
            mv /etc/rc.local_bk /etc/rc.local
        fi
    fi
    if [ ! -x "/etc/rc.local" ]; then
        chmod +x /etc/rc.local
    fi
}

start() {
    pipe_init
    ${AGENT_CMD} up -d
    ${DOCKER_COMPOSE_CMD} up -d epc-db epc-api epc-mdns epc-radius epc-raccoon
}

#######################################
# Start Otter after waiting for epc-api to finish initializing database.
# Arguments:
#   None
#######################################
start_otter() {
    ${DOCKER_COMPOSE_CMD} up -d epc-otter
    docker start epc-dbarbiter >/dev/null 2>&1
    ip route get 1.2.3.4 | tr -d '\n' | awk -v model="$MODEL" {'print model"_IP: " $7 ":8080"'}
}

status() {
    code=0
    if [ -f $ENV_FILE ]; then
        current_version=$(cat $ENV_FILE | grep VERSION | sed 's/VERSION=//')
        echo "Epc version: $current_version"
    else
        echo "Epc version: unknown. (env file $ENV_FILE not found)"
    fi

    output="Service not running: "
    for service in "epc-agent" "epc-api" "epc-db" "epc-raccoon" "epc-otter" "epc-mdns" "epc-radius";
    do
        if [ -z "$(docker ps | grep $service)" ]; then
            output="$output$service, "
            code=1
        elif [ "$(docker inspect --format '{{json .State.Running}}' $service)" != "true" ]; then
            output="$output$service, "
            code=1
        fi
    done

    if [ -z $(ps aux | grep fitdog | grep -v grep | awk '{print $1}') ]; then
        output="$output fitdog, "
        code=1
    fi

    if [ -z $(ps aux | grep host.sh | grep -v grep | awk '{print $1}') ]; then
        output="$output host_listener, "
        code=1
    fi
    if [ $code -eq 0 ]; then
        echo "All services are running"
    else
        echo ${output%??}
    fi
    return $code
}

create_uuid() {
    docker exec -it epc-api sh -c 'python /app/create_uuid.pyc'
}

db_init() {
    # Waiting for all services getting ready, and then import default data to DB
    rt=$INIT_TIMEOUT
    printf "Waiting for DB initialize "
    while [ "$(check_db_status)" -ne 0 ]
    do
        sleep 1
        rt="$((rt-1))"
        printf "."
        if [ "$rt" -eq 0 ]; then
            printf "\nNeed to import default data later because one or more $MODEL services can not start."
            exit 1
        fi
    done
    while [ ! $(docker exec -it epc-api sh -c 'python /app/db-init.pyc -t') -eq 1 ]
    do
        sleep 1
        printf "."
    done
    if [ $keep_license -eq 0 ]; then
        docker exec -it epc-api sh -c 'python /app/db-init.pyc -i >/dev/null 2>&1'
    else
        echo "Import License Data"
        docker exec -it epc-api sh -c 'python /app/db-init.pyc -li >/dev/null 2>&1'
    fi
    printf " ${GREEN}OK${NC}\n"
}

check_db_status() {
    ret=0
    #for proc in "db:mongod" "db:redis" "api:nginx" "api:gunicorn";
    for proc in "mongod" "redis" "nginx" "gunicorn";
    do
        if [ -z "$(pgrep -f $proc)" ]; then
            #echo "$proc is not running"
            ret=1
        fi
        #docker exec -it "epc-$name" sh -c 'pgrep $proc'
    done
    echo $ret
}

uninstall(){
    echo "Do you want to keep licenses?[y/n]"
    read keep
    if [ $keep = "y" ]; then
        echo "Keep Licenses, EPC Serial Number, and UUID"
        docker exec -it epc-api sh -c 'python /app/db-init.pyc -kl'
        if [ -f $EPC_PIPE_PATH/$EPC_YML ]; then stop; fi
            # remove images
            if [ ! -f $ENV_FILE ]; then echo "[ERROR] Can not get $MODEL config." && exit 1; fi
            tag=$(grep '^VERSION=' ${ENV_FILE} | cut -d'=' -f 2)
            #echo "${tag}"
            if [ $ENVIRONMENT -eq 0 ]; then
                for IMAGE in "epc-agent" "epc-api" "epc-db" "epc-raccoon" "epc-otter" "epc-mdns" "epc-radius";
                do
                    docker rmi ${REPO}${IMAGE}:${tag} >/dev/null 2>&1
                echo "${REPO}$IMAGE:${tag}"
                done
            fi
    elif [ $keep = "n" ]; then
        keep_license=0
        if [ -f $EPC_PIPE_PATH/$EPC_YML ]; then stop; fi
            # remove images
            if [ ! -f $ENV_FILE ]; then echo "[ERROR] Can not get $MODEL config." && exit 1; fi
            tag=$(grep '^VERSION=' ${ENV_FILE} | cut -d'=' -f 2)
            #echo "${tag}"
            if [ $ENVIRONMENT -eq 0 ]; then
                for IMAGE in "epc-agent" "epc-api" "epc-db" "epc-raccoon" "epc-otter" "epc-mdns" "epc-radius";
                do
                    docker rmi ${REPO}${IMAGE}:${tag} >/dev/null 2>&1
                echo "${REPO}$IMAGE:${tag}"
                done
            fi
        rm -rf $EPC_PATH $EPC_LOG_PATH /srv/docker
    else
        echo "Please Choose "y" or "n" !"
        exit
    fi

    if [ -f "/etc/rc.local" ]; then sed -i "/\/epc\/pipe\/fitdog &/d" /etc/rc.local; fi
    echo "$MODEL uninstallation was successful."
}

stop(){
    ${AGENT_CMD} down
    ${DOCKER_COMPOSE_CMD} down
    docker stop epc-dbarbiter >/dev/null 2>&1 && docker rm epc-dbarbiter >/dev/null 2>&1
    ps -ef | grep fitdog | grep -v grep | awk '{print $2}' | xargs kill >/dev/null 2>&1
    ps -ef | grep host.sh | grep -v grep | awk '{print $2}' | xargs kill >/dev/null 2>&1
}

remove_old_container(){
    if [ ! -f ${AGENT_ENV} ]; then
        docker rm -f epc-agent
    else
        ${AGENT_CMD} down
    fi
    ${DOCKER_COMPOSE_CMD} down
    docker stop epc-dbarbiter >/dev/null 2>&1 && docker rm epc-dbarbiter >/dev/null 2>&1
    ps -ef | grep fitdog | grep -v grep | awk '{print $2}' | xargs kill >/dev/null 2>&1
    ps -ef | grep host.sh | grep -v grep | awk '{print $2}' | xargs kill >/dev/null 2>&1
}

upgrade(){
    current_version=0
    if [ ! -z $1 ]; then LATEST_VERSION=$1; fi
    if [ -f $ENV_FILE ]; then current_version=$(cat $ENV_FILE | grep VERSION | sed 's/VERSION=//'); fi
    if [ "$current_version" = "0" ]; then
        echo "[ERROR] Can not get current $MODEL version."
        exit 1;
    fi
    if [ "${current_version}" = "${LATEST_VERSION}" ]; then
        echo "Current version: ${current_version} is up to date."
        exit 0
    fi
    echo "Upgrade from ${current_version} to ${LATEST_VERSION}"
    create_folders
    update_pkg
    pull_docker_images
    echo "Stopping $current_version ..."
    remove_old_container

    # Start new containers
    echo "Creating $LATEST_VERSION ..."
    download_inst_files
    setup_env
    start
    start_otter
    # Delete old images
    # echo "Delete old images: ${current_version}"
    for IMAGE in "epc-agent" "epc-api" "epc-db" "epc-raccoon" "epc-otter" "epc-mdns" "epc-radius";
    do
        docker rmi "${REPO}${IMAGE}:${current_version}" >/dev/null 2>&1
    done
    sync
    echo "$MODEL upgraded to the latest version."
}

inspect
case "$1" in
    install)
        install $2
        ;;
    uninstall)
        uninstall
        ;;
    upgrade)
        upgrade $2
        ;;
    status)
        status
        ;;
    info)
        info
        ;;
    up)
        start
        start_otter
        ;;
    down)
        stop
        ;;
    *)
    echo "Usage: $0 [install, uninstall, upgrade, status, info, up, down]"
esac
exit 0
