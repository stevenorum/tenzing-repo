# tenzing-repo

Serverless pip repo to make it easier to consume packages that you don't want to push up to Pip.

Can be deployed automatically using the [codepipeline-lambda.cf.json template](https://github.com/stevenorum/cloudformation-templates/blob/master/templates/codepipeline-lambda.cf.json) in [stevenorum/cloudformation-templates](https://github.com/stevenorum/cloudformation-templates).

Currently still janky and in the early stages of development.  I'm still working on porting the API over from the earlier version of this, so you can only upload packages to the repo by manually uploading them to the correct location in the S3 bucket.  That said, listing and downloading packages seems to work correctly.
