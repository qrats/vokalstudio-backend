## Authorize Invited User API

#### 1. Authorize

- URL: `https://api.virtualstudio.host/api/studio/authorize`
- Method: `POST`
- Header: `Content-Type: application/json`
- Request Body: `Json body`
- Response: `Json body`
- Status Code:
    + Authorization success: `200`
    + Authorization failed: `401`
    + Bad request: `400`
    + Internal server error: `500`

##### Ex. 
- Request
```text
curl --location --request POST 'http://192.168.79.167:5000/api/studio/authorize' \
--header 'Content-Type: application/json' \
--data-raw '{
    "studio_id": "dev-admin",
    "username": "gold.denis@outlook.com",
    "password": "password"
}'
```
- Response
```text
{
    "data": "Authorization success!",
    "error": false
}
```
