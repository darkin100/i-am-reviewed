I have the cust action being pulled down and running from the test repo 

    https://github.com/darkin100/commit-changes-testing

The entry to the Github action is the `action.yml` file.

We want the docker image to be very relaxed as to what it recieves, e.g all scenarios. And then the Agent will orchestrate what needs to be done.


The action is references by the tag in the client repo

    uses: darkin100/i-am-reviewed@v1.0

Therefore any changes need to be tagged for them to get pulled into the client workflow.

To update the tags, delete the tag from the UI in GitHub

    https://github.com/darkin100/i-am-reviewed/tags

Then pull the latest changed, this will delete the tag locally

Then re-tag the commit

    git tag -a -m "Test Release" v1.0
    git push --follow-tags




The docker repository 

    europe-west2-docker.pkg.dev/iamreleased/docker-images