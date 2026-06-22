#!/usr/bin/with-contenv bashio

export LOG_LEVEL="$(bashio::config 'log_level')"
RESTART_HOMEASSISTANT="$(bashio::config 'restart_homeassistant')"

SOURCE="/app/custom_components/enaro_shopping"
TARGET="/config/custom_components/enaro_shopping"
TMP_TARGET="/config/custom_components/.enaro_shopping.tmp"
OLD_TARGET="/config/custom_components/.enaro_shopping.old"

bashio::log.info "Installiere Enaro Integration..."

create_restart_notification() {
  local message
  message="Die Enaro Integration wurde installiert oder aktualisiert. Bitte Home Assistant neu starten, damit neue Plattformen, Entitaeten und Optionen geladen werden. Wenn das kuenftig automatisch passieren soll, aktiviere im Add-on die Option restart_homeassistant."

  curl -fsS -X POST \
    -H "Authorization: Bearer ${SUPERVISOR_TOKEN}" \
    -H "Content-Type: application/json" \
    -d "{\"title\":\"Enaro Integration aktualisiert\",\"message\":\"${message}\",\"notification_id\":\"enaro_integration_restart_required\"}" \
    "http://supervisor/core/api/services/persistent_notification/create" >/dev/null || {
      bashio::log.warning "Home-Assistant-Neustart-Hinweis konnte nicht als Benachrichtigung erstellt werden."
      return 1
    }
}

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
  bashio::log.warning "Bitte Home Assistant neu starten, damit die Enaro Integration vollstaendig geladen wird."
  create_restart_notification || true
fi
