# Step 1: Create a Google OAuth 2.0 Client

Go to the Google Developer Console.
Create a new project or select an existing one.
Navigate to "Credentials", then click on "Create Credentials" and choose "OAuth client ID".
Configure the consent screen if prompted.
For the application type, select "Web application".
Add authorized redirect URIs. These will be the Cognito URLs which Google will redirect to after authentication. Typically, they look like https://${your_domain}.auth.region.amazoncognito.com/oauth2/idpresponse. You'll set the exact value in the Cognito setup later.
Once created, note down the Client ID and Client Secret.

# Step 2: Store Google OAuth Credentials in AWS Secrets Manager

Go to the AWS Management Console.
Navigate to Secrets Manager and choose "Store a new secret".
Select "Other type of secrets".
Input the Google OAuth clientId and clientSecret as key-value pairs. For example:
Key: clientId, Value: <YOUR_GOOGLE_CLIENT_ID>
Key: clientSecret, Value: <YOUR_GOOGLE_CLIENT_SECRET>
Follow the prompts to name and describe the secret. Remember the secret name as you will need it in your CDK code. For example, googleOAuthCredentials.
Review and store the secret.

# Step 3: Update cdk.json

In your cdk.json file, add the configuration for your identity providers

## Attention

### Uniqueness

The userPoolDomainPrefix must be globally unique across all Amazon Cognito users. If you choose a prefix that's already in use by another AWS account, the creation of the user pool domain will fail. It's a good practice to include identifiers, project names, or environment names in the prefix to ensure uniqueness.

like so:

```json
{
  "context": {
    // ...
    "identityProviders": [
      {
        "service": "google",
        "clientId": "<YOUR_GOOGLE_CLIENT_ID_SECRET_NAME>",
        "clientSecret": "<YOUR_GOOGLE_CLIENT_SECRET_NAME>"
      }
    ],
    "userPoolDomainPrefix": "<UNIQUE_DOMAIN_PREFIX_FOR_YOUR_USER_POOL>"
  }
}
```

# Step 4: Deploy Your CDK Stack

Deploy your CDK stack to AWS:

```sh
cdk deploy --require-approval never --all
```

# Step 5: Update Google OAuth Client with Cognito Redirect URIs

After deploying your stack, go back to the Google Developer Console and update the OAuth client with the correct redirect URIs. You can find these URIs in the Cognito console under the domain name configuration for your user pool.