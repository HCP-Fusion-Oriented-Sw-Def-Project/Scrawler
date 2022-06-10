# Scrawler 

###### An automated tool to crawl Android apps and detect changes of GUI at the function level.

## Requirement

######
* Android SDK 
* Android devices or emulators.
* Python 3.7.6
* All the other requirements are listed in the requirements.txt.

## Connect devices
######
1. Connect devices via the adb tool.
2. Execute adb command in the terminal, e.g.,`adb connect`.
######

## Crawl an app

######
Setting the parameters in the script file  `crawler.py`:
* save directory ` obj = Crawler(package_name, save_dir)`.
* `max_depth`
* `max_time`
* `action_interval` time interval between two adjacent actions.
* `replay_try_times`  number of attempts to traverse back to the previous screen.
* `repoen_to_first` whether returning to the main screen when reopening the app.
* `distinct_rate`  threshold to distinct different screens.
* `black_elem_list` element black list.
* `black_screen_list` screen black list.
* `act_max_count` maximum number of screen per activity collected.
* `black_act_list` activity black list.
