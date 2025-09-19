action-railway-redeploy
===


Trigger reploy for railway, Inspired by [How to automatically re-deploy when a new docker image is published?](https://help.railway.app/questions/how-to-automatically-re-deploy-when-a-ne-c181402a)


```
- uses: repotea-workspace/kangumi/github-actions/railway-redeploy@main
  with:
    railway_token: ${{ secrets.RAILWAY_TOKEN }}
    environment_id: "4dedc55b-f25a-4ebf-0000-58bc04c48bce"
    service_id: "4564b9b1-29dc-4526-0000-b5f3c0606a14"
```
