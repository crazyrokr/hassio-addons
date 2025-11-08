ARG BUILD_FROM
FROM $BUILD_FROM

RUN mkdir /share
RUN echo "[ -f /config/.config/obsidian/obsidian.json ] || \
    (cd /config/.config && mkdir obsidian && chown abc:abc obsidian && \
    echo '{\"frame\":\"native\",\"updateDisabled\":true}' > obsidian/obsidian.json && \
    chown abc:abc obsidian/obsidian.json)" >> /etc/s6-overlay/s6-rc.d/init-obsidian-config/run
