[app]
title = Minecraft 2D
package.name = minecraft2d
package.domain = org.minecraft2d
source.dir = .
source.include_exts = py,png,jpg,jpeg,ogg,wav,mp3,json
version = 1.0
requirements = python3,pygame-ce
orientation = landscape
fullscreen = 1
icon.filename = %(source.dir)s/icon.png
p4a.bootstrap = sdl2
p4a.local_recipes = %(source.dir)s/p4a-recipes

android.minapi = 21
android.archs = arm64-v8a,armeabi-v7a
android.allow_backup = True
android.accept_sdk_license = True

[buildozer]
log_level = 2
warn_on_root = 1
