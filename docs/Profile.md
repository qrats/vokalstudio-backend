## Profile API

#### 1. Get profile

- URL: `${BASE_URL}/profile`
- Method: `GET`
- Authentication: `Bearer ${ACCESS_TOKEN}`
- Header: `None`
- Request Body: `None`
- Response: `Profile data`
- Status Code:
    + Succsss: `200`
    + Entity not exist: `404`
    + Internal server error: `500`

##### Ex. 
- Request
```text
curl --location --request GET '${BASE_URL}/profile' \
--header 'Authorization: Bearer ${ACCESS_TOKEN}'
```
- Response
```text
{
  "email": "admin@yahoo.com",
  "first_name": "John",
  "id": 14,
  "last_name": "Doe",
  "phone_number": null,
  "role": "Admin",
  "verified": false
}
```

#### 2. Update

- URL: `${BASE_URL}/profile`
- Method: `PUT`
- Authentication: `Bearer ${ACCESS_TOKEN}`
- Header: `Content-Type: application/json`
- Request Body: `json body`
- Response: Profile
- Status Code:
    + Succsss: `200`
    + Entity not exist: `404`
    + Internal server error: `500`

##### Ex. 
- Request
```text
curl --location --request PUT '${BASE_URL}/profile' \
--header 'Authorization: Bearer ${ACCESS_TOKEN}' \
--header 'Content-Type: application/json' \
--data-raw '{
  "email": "admin@yahoo.com",
  "first_name": "John",
  "last_name": "Brook",
  "phone_number": "207-731-8826",
  "role": "Admin"
}'
```
- Response
```text
{
  "email": "admin@yahoo.com",
  "first_name": "John",
  "id": 14,
  "last_name": "Brook",
  "phone_number": "207-731-8826",
  "role": "Admin",
  "verified": false
}
```

#### 3. Password Reset

- URL: `${BASE_URL}/profile/password-reset`
- Method: `PUT`
- Authentication: `Bearer ${ACCESS_TOKEN}`
- Header: `Content-Type: application/json`
- Request Body: `json body`
- Response: success message
- Status Code:
    + Succsss: 200
    + Bad request: 400
    + Entity not exist: 404
    + Internal server error: 500

##### Ex. 
- Request
```text
curl --location --request GET '${BASE_URL}/profile/password-reset' \
--header 'Content-Type: application/json' \
--header 'Authorization: Bearer ${ACCESS_TOKEN}' \
--data-raw '{
    "email": "admin@yahoo.com",
    "current_password": "password123P!",
    "new_password": "newpwd123P!"
}'
```
- Response
```text
{
    "message": "Password reset success!"
}
```