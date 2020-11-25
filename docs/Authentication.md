## Authentication API

#### 1. Signup

- URL: `${BASE_URL}/auth/sign-up`
- Method: `POST`
- Header: `Content-Type: application/json`
- Request Body: `Json body`
- Response: `Auth Token`
- Status Code:
    + Signup success: `201`
    + Bad request: `400`
    + Internal server error: `500`

##### Ex. 
- Request
```text
curl --location --request POST '${BASE_URL}/auth/sign-up' \
--header 'Content-Type: application/json' \
--data-raw '{
    "email": "admin@yahoo.com",
    "password": "password123P!",
    "role": "Admin",
    "first_name": "John",
    "last_name": "Doe"
}'
```
- Response
```text
{
  "access_token": "XXX.XXX.XXX",
  "refresh_token": "XXX.XXX.XXX"
}
```

#### 2. Signin

- URL: `${BASE_URL}/auth/sign-in`
- Method: `POST`
- Header: `Content-Type: application/json`
- Request Body: `Json body`
- Response: `Auth Token`
- Status Code:
    + Signin success: `200`
    + Bad request: `400`
    + Internal server error: `500`

##### Ex. 
- Request
```text
curl --location --request POST '${BASE_URL}/auth/sign-in' \
--header 'Content-Type: application/json' \
--data-raw '{
    "email": "admin@gmail.com",
    "password": "password123P!"
}'
```
- Response
```text
{
  "access_token": "XXX.XXX.XXX",
  "refresh_token": "XXX.XXX.XXX"
}
```