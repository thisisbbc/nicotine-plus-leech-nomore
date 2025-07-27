# SPDX-FileCopyrightText: 2020-2025 Nicotine+ Contributors
# SPDX-FileCopyrightText: 2011 quinox <quinox@users.sf.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from pynicotine.pluginsystem import BasePlugin


class Plugin(BasePlugin):

    PLACEHOLDERS = {
        "%files%": "num_files",
        "%folders%": "num_folders"
    }

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

        self.settings = {
            "message": "You are sharing less than 100 files, please consider sharing more files if you would like to download from me again. Thanks :)",
            "messageban": (
                "It looks like you're not sharing anything, so you've been automatically banned."
                "Please consider sharing more files if you would like to download from me again. Thanks :)"
            ),
            "num_files": 100,
            "num_folders": 1,
            "open_private_chat": True,
            "ban_zero_files": True,
            "detected_leechers": []
        }
        self.metasettings = {
            "message": {
                "description": (
                    "Private chat message to send to leechers. Each line is sent as a separate message, "
                    "too many message lines may get you temporarily banned for spam!"
                ),
                "type": "textview"
            },
            "messageban": {
                "description": "If enabled, this message will be sent to users that share zero files.",
                "type": "textview"
            },
            "num_files": {
                "description": "Require users to have a minimum number of shared files:",
                "type": "int", "minimum": 0
            },
            "num_folders": {
                "description": "Require users to have a minimum number of shared folders:",
                "type": "int", "minimum": 1
            },
            "open_private_chat": {
                "description": "Open chat tabs when sending private messages to leechers",
                "type": "bool"
            },
            "ban_zero_files": {
                "description": "Ban users that share zero files",
                "type": "bool"
            },
            "detected_leechers": {
                "description": "Detected leechers",
                "type": "list string"
            }
        }

        self.probed_users = {}

    def loaded_notification(self):

        min_num_files = self.metasettings["num_files"]["minimum"]
        min_num_folders = self.metasettings["num_folders"]["minimum"]

        if self.settings["num_files"] < min_num_files:
            self.settings["num_files"] = min_num_files

        if self.settings["num_folders"] < min_num_folders:
            self.settings["num_folders"] = min_num_folders

        if not (self.settings["message"] and self.settings["messageban"] and
                self.settings["ban_zero_files"]):
            self.log(
                "No warning or ban message configured and turbo leechers will not be banned."
            )
        elif (self.settings["message"] and not self.settings["messageban"] and not
                self.settings["ban_zero_files"]):
            self.log(
                "Ready to warn users that share less than %d files in %d shared public folders.",
                (self.settings["num_files"], self.settings["num_folders"])
            )
            self.log(
                "No ban message configured and turbo leechers will not be banned."
            )
        elif (self.settings["message"] and self.settings["messageban"] and not
                self.settings["ban_zero_files"]):
            self.log(
                "Ready to warn users that share less than %d files in %d shared public folders.",
                (self.settings["num_files"], self.settings["num_folders"])
            )
            self.log(
                "Turbo leechers will be warned but will not be banned."
            )
        elif (self.settings["message"] and self.settings["messageban"] and
                self.settings["ban_zero_files"]):
            self.log(
                "Ready to warn users that share less than %d files in %d shared public folders.",
                (self.settings["num_files"], self.settings["num_folders"])
            )
            self.log(
                "Turbo leechers will be warned and banned."
            )
        else:
            pass

    def check_user(self, user, num_files, num_folders, source="server"):

        if user not in self.probed_users:
            # We are not watching this user
            return

        if self.probed_users[user] == "okay":
            # User was already accepted previously, nothing to do
            return

        if self.probed_users[user] == "requesting_shares" and source != "peer":
            # Waiting for stats from peer, but received stats from server. Ignore.
            return

        is_user_accepted = (num_files >= self.settings["num_files"] and num_folders >= self.settings["num_folders"])

        if is_user_accepted or user in self.core.buddies.users:
            if user in self.settings["detected_leechers"]:
                self.settings["detected_leechers"].remove(user)

            self.probed_users[user] = "okay"

            if is_user_accepted:
                self.log("User %s is okay, sharing %s files in %s folders.", (user, num_files, num_folders))
            else:
                self.log("Buddy %s is sharing %s files in %s folders. Not complaining.",
                         (user, num_files, num_folders))
            return

        if not self.probed_users[user].startswith("requesting"):
            # We already dealt with the user this session
            return

        if user in self.settings["detected_leechers"]:
            # We already messaged the user in a previous session
            self.probed_users[user] = "processed_leecher"
            return

        if (num_files <= 0 or num_folders <= 0) and self.probed_users[user] != "requesting_shares":
            # SoulseekQt only sends the number of shared files/folders to the server once on startup.
            # Verify user's actual number of files/folders.
            self.log("User %s has no shared files according to the server, requesting shares to verify…", user)

            self.probed_users[user] = "requesting_shares"
            self.core.userbrowse.request_user_shares(user)
            return

        if (self.settings["message"] and num_files > 0):
            log_message = ("Leecher detected, %s is only sharing %s files in %s folders. Going to warn them after transfer")
            self.probed_users[user] = "pending_leecher"
            self.log(log_message, (user, num_files, num_folders))
        elif(not self.settings["message"] and num_files > 0):
            log_message = ("Leecher detected, %s is only sharing %s files in %s folders. Going to log them after transfer")
            self.probed_users[user] = "pending_leecher"
            self.log(log_message, (user, num_files, num_folders))
        elif(self.settings["messageban"] and num_files == 0 and self.settings["ban_zero_files"]):
            log_message = ("Turbo leecher detected, %s is very naughty, let's warn and ban them after transfer")
            self.probed_users[user] = "pending_turboleecher"
            self.log(log_message, user)
        elif(not self.settings["messageban"] and num_files == 0 and self.settings["ban_zero_files"]):
            log_message = ("Turbo leecher detected, %s is very naughty, let's ban them after transfer")
            self.probed_users[user] = "pending_turboleecher"
            self.log(log_message, user)
        elif(not self.settings["messageban"] and num_files == 0 and not self.settings["ban_zero_files"]):
            log_message = ("Turbo leecher detected, %s is very naughty and will be logged after transfer")
            self.probed_users[user] = "pending_turboleecher"
            self.log(log_message, user)
        else:
            pass

    def upload_queued_notification(self, user, virtual_path, real_path):

        if user in self.probed_users:
            return

        self.probed_users[user] = "requesting_stats"

        if user not in self.core.users.watched:
            # Transfer manager will request the stats from the server shortly
            return

        # We've received the user's stats in the past. They could be outdated by
        # now, so request them again.
        self.core.users.request_user_stats(user)

    def user_stats_notification(self, user, stats):
        self.check_user(user, num_files=stats["files"], num_folders=stats["dirs"], source=stats["source"])

    def upload_finished_notification(self, user, *_):

        if user not in self.probed_users:
            return

        if self.probed_users[user] not in ("pending_leecher", "pending_turboleecher"):
            return

        if (self.probed_users[user] == "pending_turboleecher" and self.settings["ban_zero_files"] and self.settings["messageban"]):
            for line in self.settings["messageban"].splitlines():
                for placeholder, option_key in self.PLACEHOLDERS.items():
                    # Replace message placeholders with actual values specified in the plugin settings
                    line = line.replace(placeholder, str(self.settings[option_key]))
                
                self.send_private(user, line, show_ui=self.settings["open_private_chat"], switch_page=False)
                
            self.core.network_filter.ban_user(user)
            self.log("Turbo Leecher %s is now banned. Message sent.", user)
            return
        elif (self.probed_users[user] == "pending_turboleecher" and self.settings["ban_zero_files"] and not self.settings["messageban"]):
            self.core.network_filter.ban_user(user)
            self.log("Turbo Leecher %s is now banned.", user)
        else:
            pass

        self.probed_users[user] = "processed_leecher"

        if not self.settings["message"]:
            self.log("Leecher %s doesn't share enough files. No message is specified in plugin settings.", user)
            return

        for line in self.settings["message"].splitlines():
            for placeholder, option_key in self.PLACEHOLDERS.items():
                # Replace message placeholders with actual values specified in the plugin settings
                line = line.replace(placeholder, str(self.settings[option_key]))

            self.send_private(user, line, show_ui=self.settings["open_private_chat"], switch_page=False)

        if user not in self.settings["detected_leechers"]:
            self.settings["detected_leechers"].append(user)

        self.log("Leecher %s doesn't share enough files. Message sent.", user)