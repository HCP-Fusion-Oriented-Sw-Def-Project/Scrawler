# Scrawler 

######
An automated tool to crawl Android apps and detect changes of GUI at the function level.

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
Set the parameters in the script file  `backend/crawler.py`:
* save_dir  the directory to save the results, e.g., ` obj = Crawler(package_name, save_dir)`.  
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
Then run the script file `backend/crawler.py`.

######
When the crawling process finished, we can get the results in the directory `save_dir/result/`:
* **images** : screenshots.
* **log**: which records the crawling process.
* **model**: containing the screens and actions.
* **traverse_graph**:  describing the crawing process.

######
Besides, the GUI data of each screen is in the directory `save_dir/screen_name`, in the form of screenshot and xml file.

## Compare the GUI models
######

1. Prepare the base and updated model of an app, and put them in the same directory we called work directory.
2. Set the work directory in the script file `backend/model_comparison.py`, e.g., `obj = Comparator('C:/Users/dell/Desktop/tmp_comparisio')`.
Then run the script file `backend/model_comparison.py`.

######
When the comparing process finished, we can get the results in the directory `work_dir/result/`:
* **edges** : record the removed, matched and added actions.
* **screens**: record the removed, matched and added screens.
* **base_graph**: show the results in the base version graph.
* **updated_graph**:  show the results in the updated version graph.

## GUI Test Repair
######
Or we can view the process as finding the new execution path of an function for the app in the updated version.

1.  Set the work directory in the script file `/get_new_path/find_path.py`.
2. Record the event sequences of an function in the base version with coordinates and Set the coordinates in the script file `/get_new_path/find_path.py`.
3. Replay the event sequences in the base version, e.g., `obj.replay()` by running the script file `/get_new_path/find_path.py` and we can get the `scenario_model` in the work directory.
4. Put the `updated_model` in the work directory.
5. Set the parameters in the script file `/get_new_path/find_path.py`:
  * `distinct_rate`: threshold to distinct different screens.
  * `text_sim`: threshold to match screens.
  * `is_circle`: whether the path in the results could contain circle.
  *  `max_candidate_num`: the maximum number of candidate paths in the result.
6.  Run the script file `/get_new_path/find_path.py`  with only `obj.work()`, in this time we need not `obj.replay()`.

When the repairing process finished, we can get the results in the directory `work_dir/result/`:
* **candidate**: all candidate paths.
* **optimal**: the best path.

