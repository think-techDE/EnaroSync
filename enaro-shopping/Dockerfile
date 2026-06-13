ARG BUILD_FROM
FROM $BUILD_FROM

WORKDIR /app

COPY custom_components/ /app/custom_components/
COPY run.sh /run.sh

RUN apk add --no-cache curl \
    && chmod +x /run.sh

CMD ["/run.sh"]
