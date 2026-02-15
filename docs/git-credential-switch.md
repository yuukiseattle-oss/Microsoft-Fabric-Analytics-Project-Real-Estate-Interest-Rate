# Git アカウント切り替え手順 (Windows)

## 状況
Windows の Git Credential Manager に古いアカウントがキャッシュされていて、
別のアカウント/Organization のリポジトリに push できない場合。

## エラー例
```
remote: Permission to org-name/repo.git denied to old-username.
fatal: unable to access '...': The requested URL returned error: 403
```

## 手順

### Step 1: Windows 資格情報マネージャーから削除
```bash
cmdkey /delete:git:https://github.com
```

### Step 2: Git Credential Manager から削除
```bash
echo -e "host=github.com\nprotocol=https" | git credential-manager erase
```

### Step 3: 削除されたことを確認
```bash
git credential-manager github list
# 何も表示されなければOK
```

### Step 4: push して再認証
```bash
git push -u origin main
# ブラウザが開くので、新しいアカウントでログイン
```

## 補足
- `git config --global credential.helper` で使用中のヘルパーを確認可能
- Windows では通常 `wincred` または `manager-core` が設定されている
- Step 1 だけでは不十分な場合がある（Git Credential Manager が別途キャッシュを持つため）
- **Step 1 と Step 2 の両方を実行するのが確実**
- `git config user.name` / `user.email` は認証とは無関係（コミット署名用）
