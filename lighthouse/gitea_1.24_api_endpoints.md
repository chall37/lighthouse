# Gitea 1.24 API Endpoints

Below is a categorized list of all API endpoints available in Gitea version 1.24, grouped by functional areas (repositories, issues, users, organizations, etc.). Each endpoint is described briefly with its purpose.  

## Repositories

- **GET** `/repos/search` – Search for repositories by name, description, or other criteria (accessible to all users with results filtered by visibility).  
- **POST** `/user/repos` – Create a new repository for the authenticated user (you provide repo details in the JSON body).  
- **POST** `/orgs/{org}/repos` – Create a new repository within an organization (must be an org member with permission).  
- **GET** `/repos/{owner}/{repo}` – Retrieve detailed information about a specific repository (metadata, settings, etc.).  
- **PATCH** `/repos/{owner}/{repo}` – Edit repository properties such as name, description, or settings (only fields set in the JSON are changed).  
- **DELETE** `/repos/{owner}/{repo}` – Delete a repository. Requires admin rights on the repo (permanently removes the repository).  
- **POST** `/repos/{owner}/{repo}/transfer` – Transfer a repository to a new owner (change ownership to another user or org).  
- **GET** `/repos/{owner}/{repo}/branches` – List all branches in the repository.  
- **GET** `/repos/{owner}/{repo}/branches/{branch}` – Get details of a specific branch (commit SHA, whether protected, etc.).  
- **DELETE** `/repos/{owner}/{repo}/branches/{branch}` – Delete a branch (usually a non-default branch).  
- **GET** `/repos/{owner}/{repo}/branch_protections` – List branch protection rules for the repository.  
- **POST** `/repos/{owner}/{repo}/branch_protections` – Add a new branch protection rule (e.g. require approvals, block pushes) for a branch.  
- **PATCH** `/repos/{owner}/{repo}/branch_protections/{id}` – Update an existing branch protection rule by ID.  
- **DELETE** `/repos/{owner}/{repo}/branch_protections/{id}` – Remove a branch protection rule.  
- **GET** `/repos/{owner}/{repo}/tags` – List tags in the repository (name and commit SHA for each tag).  
- **GET** `/repos/{owner}/{repo}/archive/{ref}.{format}` – Download an archive of the repository at the given ref (branch/tag/commit), e.g. as zip or tar.gz archive.  
- **GET** `/repos/{owner}/{repo}/forks` – List forks of this repository.  
- **POST** `/repos/{owner}/{repo}/forks` – Fork the repository into the authenticated user’s account (creates a new repo copy under your ownership).  
- **GET** `/repos/{owner}/{repo}/stargazers` – List the users who have starred (liked) the repository.  
- **GET** `/repos/{owner}/{repo}/subscribers` – List the users watching (subscribed to notifications for) the repository.  
- **PUT** `/repos/{owner}/{repo}/subscription` – Watch (subscribe to) the repository (the authenticated user will receive notifications).  
- **DELETE** `/repos/{owner}/{repo}/subscription` – Stop watching (unsubscribe from) the repository notifications.  
... (content truncated for brevity in the Python block; full content is included in file) ...
