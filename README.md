# Python Release Script

This was a take home assignment that I completed as part of a take home test for
the interview process at a firm that I applied to.

The requirements were:

>Every Friday the Release Manager does a code freeze in preparation for the next release. Currently the Release Manager does all the code freeze work manually.
The Release Manager's code freeze process involves: 
>
>- Updating `release.plist` file with release name/version for the next release found in `releng/release_info.csv`.
>- Performing the code freeze by cutting a new branch with from the base branch with name `release_name/release_version` e.g. `Date/1.3`. 
>- Generating a Feature Flag report which is a diff between the current and the previous release of the file `featureflags/FF.csv` 
>
>Your task is to implement a command line tool to help automate as much of our
code freeze process as possible. When designing your tool, consider that it
would be used by folks with less technical expertise. The tool should also be
able to handle some exceptions and fail gracefully. 
>
>Feel free to use your favorite programming language and framework (we use Python internally) but the code should be able to run on modern Mac hardware and OS. 
>
>Plan for the tool to be extended over time, and use of the Github API is prefered.
