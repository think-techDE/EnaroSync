#!/usr/bin/with-contenv bashio

export LOG_LEVEL="$(bashio::config 'log_level')"
RESTART_HOMEASSISTANT="$(bashio::config 'restart_homeassistant')"

SOURCE="/app/custom_components/enaro_shopping"
TARGET="/config/custom_components/enaro_shopping"
TMP_TARGET="/config/custom_components/.enaro_shopping.tmp"
OLD_TARGET="/config/custom_components/.enaro_shopping.old"

bashio::log.info "Installiere Enaro Integration..."

if [ ! -d "${SOURCE}" ]; then
  bashio::log.fatal "Integrationsquelle fehlt: ${SOURCE}"
  exit 1
fi

mkdir -p /config/custom_components

if [ -d "${TARGET}" ] && [ ! -f "${TARGET}/.enaro-managed" ]; then
  bashio::log.fatal "Ziel ${TARGET} existiert, ist aber nicht von diesem Add-on verwaltet. Bitte vorher manuell sichern oder entfernen."
  exit 1
fi

rm -rf "${TMP_TARGET}" "${OLD_TARGET}"
mkdir -p "${TMP_TARGET}"
cp -a "${SOURCE}/." "${TMP_TARGET}/"
touch "${TMP_TARGET}/.enaro-managed"

if [ -d "${TARGET}" ]; then
  mv "${TARGET}" "${OLD_TARGET}"
fi
mv "${TMP_TARGET}" "${TARGET}"
rm -rf "${OLD_TARGET}"

bashio::log.info "Enaro Integration wurde nach ${TARGET} installiert/aktualisiert."

if [ "${RESTART_HOMEASSISTANT}" = "true" ]; then
  bashio::log.warning "Home Assistant wird neu gestartet, damit die Integration geladen wird..."
  curl -fsS -X POST \
    -H "Authorization: Bearer ${SUPERVISOR_TOKEN}" \
    -H "Content-Type: application/json" \
    "http://supervisor/core/restart" || {
      bashio::log.error "Home Assistant Neustart konnte nicht ausgeloest werden."
      exit 1
    }
else
  bashio::log.info "Bitte Home Assistant neu starten und danach unter Einstellungen > Geraete & Dienste die Integration 'Enaro Integration' hinzufuegen."
fi
