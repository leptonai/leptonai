# Error Patch Deployment

### Date
2023.08.11

### Author
Yadong Xie

### Summary

Patch the data of the deployment incorrectly in the frontend, resulting in the content of mounts being cleared.

### Impact

When users modify the replica quantity, the mounts data is cleared, resulting in a failed startup of the user's deployment.

### Timeline

### Root Causes

https://github.com/leptonai/lepton/blob/55e1bbe269bb56c20b9218ea17626947905c7942/web/src/routers/workspace/components/deployment-form/index.tsx#L227

When editing, there is no distinction between creating a new one and editing an existing one. In this case, the "mounts" are disabled, causing the function to receive no "mounts" keys here, which is then incorrectly sent to the backend after being supplemented with [].

### Resolution

- Send a PR to fix this
- Patched the deployment from the previous backup. so user deployment is restored.

### Detection

### Action Items

In the front-end, it is necessary to introduce more e2e testing to solve these problems.

### Lessons Learned

#### What went well

#### What went wrong
