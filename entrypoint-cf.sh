# Redis
redis_credentials="$(echo "${VCAP_SERVICES}" | jq -r '.["rediscloud"][0].credentials // ""')"
if [ -z "${redis_credentials}" ]; then
  echo "Error: Please bind a redis service" >&2
  exit 1
fi
REDIS_HOST="$(echo "${redis_credentials}" | jq -r '.hostname // ""')"
REDIS_PORT="$(echo "${redis_credentials}" | jq -r '.port // ""')"
REDIS_PASSWORD="$(echo "${redis_credentials}" | jq -r '.password // ""')"

echo "credentials: ${redis_credentials}"
export REDIS_HOST REDIS_PORT REDIS_PASSWORD

echo "web port: ${PORT}"

# Start
flask run
