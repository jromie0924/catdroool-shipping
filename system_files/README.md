# Setting this service up to run as a scheduled daemon

Copy both of these files in `/lib/systemd/system` and ensure that they are owned by `root:root` and have `644` permissions

Modern linux systems run with SELinux, which produces a hurdle in getting the system access to run the script that starts the catdroool service.

run the following commands:

`sudo semanage fcontext -a -t init_exec_t "<script location>"`

`sudo restorecon -v <script location>`

`sudo systemctl enable schedule-catdroool.timer`