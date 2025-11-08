ARG BUILD_FROM
FROM $BUILD_FROM

RUN mkdir /share
RUN sed -i 's/<application class="\*">/&<decor>no<\/decor>/' /etc/xdg/openbox/rc.xml
RUN echo "cd /config/.config && mkdir -p obsidian && chown abc:abc obsidian && \
    echo '{\"frame\":\"native\",\"updateDisabled\":true}' > obsidian/obsidian.json && \
    chown abc:abc obsidian/obsidian.json" >> /etc/s6-overlay/s6-rc.d/init-obsidian-config/run
