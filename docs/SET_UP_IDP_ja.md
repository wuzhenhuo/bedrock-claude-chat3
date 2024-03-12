# ステップ 1: Google OAuth 2.0 クライアントを作成する

1. Google Developer Console へ移動します。
2. 新しいプロジェクトを作成するか、既存のプロジェクトを選択します。
3. 「認証情報」に移動し、「認証情報を作成」をクリックして「OAuth クライアント ID」を選択します。
4. 促された場合、同意画面を設定します。
5. アプリケーションタイプとして「Web アプリケーション」を選択します。
6. 承認されたリダイレクト URI を追加します。これらは、認証後に Google がリダイレクトする Cognito の URL になります。一般的に、これらは https://${your_domain}.auth.region.amazoncognito.com/oauth2/idpresponse のように見えます。Cognito の設定で後ほど正確な値を設定します。[Step5 を参照](#ステップ-5-cognito-リダイレクト-uri-で-google-oauth-クライアントを更新する)
7. 作成されたら、クライアント ID とクライアント シークレットをメモしてください。

# ステップ 2: AWS Secrets Manager に Google OAuth 資格情報を保存する

1. AWS 管理コンソールへ移動します。
2. Secrets Manager に移動し、「新しいシークレットを保存」を選択します。
3. 「他のタイプのシークレット」を選択します。
4. Google OAuth clientId と clientSecret をキーと値のペアとして入力します。例えば：
   キー: clientId, 値: <YOUR_GOOGLE_CLIENT_ID>
   キー: clientSecret, 値: <YOUR_GOOGLE_CLIENT_SECRET>
5. シークレットの名前と説明を入力して進んでください。CDK コードで必要になるので、シークレット名を覚えておいてください。例：googleOAuthCredentials。
6. シークレットを確認して保存します。

# ステップ 3: cdk.json を更新する

cdk.json ファイルに、あなたのアイデンティティプロバイダーの設定を追加します。

## 注意

### ユニークさ

userPoolDomainPrefix は、すべての Amazon Cognito ユーザー間でグローバルにユニークでなければなりません。他の AWS アカウントですでに使用されているプレフィックスを選択した場合、ユーザープールドメインの作成が失敗します。プレフィックスに識別子、プロジェクト名、または環境名を含めることは、ユニークさを確保するための良い実践です。

以下のようにします：

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

# ステップ 4: CDK スタックをデプロイする

AWS に CDK スタックをデプロイします：

```sh
cdk deploy --require-approval never --all
```

# ステップ 5: Cognito リダイレクト URI で Google OAuth クライアントを更新する

スタックをデプロイした後、CfnOutput で AuthApprovedRedirectURI が出力されます。
Google Developer Console に戻り、OAuth クライアントを正しいリダイレクト URI で更新します。これらの URI は、Cognito コンソールのユーザープールのドメイン名設定の下にあります。