#!/usr/bin/env python
#
# Author: Karl A. Krueger
# This file is released into the public domain.
#

VERSION = "1.1"

USAGE = """
photosort.py -- a tool for sorting pictures into directories

Usage:
  ./photosort.py source dest1 [dest2 ...]

source must be a directory containing only images.
destinations may be existing directories or unused names.

Example:
  ./photosort.py myphotos Cool Awesome Trash

photosort.py will create destination directories if needed.
It will not overwrite existing files.

Keyboard commands:
  space bar to toggle destinations,
  shift-S to save and exit,
  shift-Q or Escape to abandon all changes and exit,
  shift-L to exit printing a filename list,
  v to toggle verbose mode (displays metadata and filename).
  c to toggle crosshairs
"""

import os, sys, time

try:
  import pygame
  import pygame.gfxdraw
except ImportError:
  print "Please install Pygame."
  print "This program uses Pygame to display graphics."
  print
  print "sudo apt-get install python-pygame"
  print
  sys.exit(1)

try:
  import kaa.metadata
except ImportError:
  print "Please install the Kaa metadata module."
  print "This program uses Kaa to read EXIF metadata from image files."
  print
  print "sudo apt-get install python-kaa-metadata"
  print
  sys.exit(1)


# These are the RGB colors to use when displaying destination tags.
destcolors = [(0, 0, 0),  # black (unused)
             (255, 0, 0), (0, 255, 0), (0, 0, 255), # red green blue
             (255, 255, 0), (255, 0, 255), (0, 255, 255), # yellow magenta cyan
             (255, 128, 0), (128, 96, 0), # orange, brown
             (0, 255, 128), (0, 128, 255), # aqua, skyblue
             (128, 0, 255), (192, 0, 128), # violet, tyrian
             (128, 255, 0), # chartreuse
             (192, 192, 192), (128, 128, 128), (64, 64, 64), # grays
             (0, 0, 0), (255, 255, 255)]   # black, white
destcolors += destcolors   # in case we have a stoned number of destinations


def proportional_scale(surf, dest):
  """Scale a Pygame surface proportionally to fit on a destination surface."""
  sx, sy = surf.get_size()
  dx, dy = dest.get_size()
  sr = float(sx) / sy   # aspect ratio
  dr = float(dx) / dy
  if sr > dr:
    x, y = dx, int(dx / sr)
  else:
    x, y = int(dy * sr), dy
  return pygame.transform.smoothscale(surf, (x,y))


def center(surf, dest):
  """Center a Pygame surface on a destination surface."""
  sx, sy = surf.get_size()
  dx, dy = dest.get_size()
  offset_x = (dx - sx) / 2
  offset_y = (dy - sy) / 2
  return offset_x, offset_y


def crosshair(surf, color=(0, 0, 0)):
  """Draw a crosshair on a Pygame surface."""
  sx, sy = surf.get_size()
  pygame.gfxdraw.hline(surf, 0, sx, (sy/2), color)
  if sy % 2 == 0:
    pygame.gfxdraw.hline(surf, 0, sx, (sy/2)+1, color)
  pygame.gfxdraw.vline(surf, (sx/2), 0, sy, color)
  if sx % 2 == 0:
    pygame.gfxdraw.vline(surf, (sx/2)+1, 0, sy, color)


class Sorter(object):
  def __init__(self, screen, directory, destinations):
    self.screen = screen
    self.directory = directory

    # Read the filenames from the source directory.
    self.filelist = os.listdir(self.directory)
    self.filelist.sort()

    # Set up the dicts for storing data about the images.
    self.photos = {}    # dictionary from filename to a pygame surface
    self.metadata = {}  # dictionary from filename to kaa metadata dictionary
    self.destmap = dict((fn, 0) for fn in self.filelist)  # file -> dest number
    self.destinations = [None] + destinations   # 0th dest means don't move

    # Miscellaneous settings
    self.font = pygame.font.SysFont("Verdana", 32)
    self.verbose = 0
    self.crosshair = 0
    self.current = 0

  def __getitem__(self, fname):
    # Instead of loading all the images at startup, we load them as the
    # user moves to them.
    if fname not in self.photos:
      self.load(fname)
    return self.photos[fname]

  def load(self, fname):
    """Add this image to our caches."""
    fullpath = os.path.join(self.directory, fname)

    # Store the image itself, scaled to the current screen size.
    surf = pygame.image.load(fullpath)
    surf = proportional_scale(surf, self.screen)
    self.photos[fname] = surf

    # Store the image metadata.
    metadata = kaa.metadata.parse(fullpath)
    self.metadata[fname] = metadata

  def writetext(self, text, (x, y), color):
    surf = self.font.render(text, True, color)
    self.screen.blit(surf, (x, y))

  def display(self, fname):
    """Display a given image."""
    surf = self[fname]
    self.screen.fill((0,0,0))
    offset_x, offset_y = center(surf, self.screen)
    self.screen.blit(surf, (offset_x, offset_y))

    # Display the currently selected destination.
    if self.destmap[fname] != 0:
      dest = self.destinations[self.destmap[fname]]
      color = destcolors[self.destmap[fname]]
      self.writetext(dest, (offset_x + 20, 20), color)

    if self.crosshair == 1:
      crosshair(self.screen, (255, 255, 255))
    elif self.crosshair == 2:
      crosshair(self.screen, (0, 0, 0))

    # If in verbose mode, display metadata.
    if self.verbose:
      # use either white or black text
      color = (255, 255, 255) if self.verbose == 1 else (0, 0, 0)

      # the description, from the exif metadata
      desc = self.metadata[fname].get("description", "No description")
      if not desc: desc = "No description"
      self.writetext(desc, (offset_x + 20, 60), color)

      # the timestamp, from the exif metadata
      date = self.metadata[fname].get("timestamp", 0)
      date = time.ctime(date) if date != None else "No timestamp"
      self.writetext(date, (offset_x + 20, 100), color)

      # the filename
      self.writetext(fname, (offset_x + 20, 140), color)

    pygame.display.flip()

  def switchdest(self, fname):
    """On keypress, switch the current image's tagged destination."""
    self.destmap[fname] = (self.destmap[fname] + 1) % len(self.destinations)

  def bailout(self):
    """Exit without saving."""
    self.writetext("Quitting ...", (20, 180), (255, 0, 0))
    pygame.display.flip()
    sys.exit(1)

  def done(self):
    """Save and exit."""
    self.writetext("Saving ...", (20, 180), (0, 192, 0))
    pygame.display.flip()
    for fname in self.filelist:
      if self.destmap[fname] != 0:
        newdir = self.destinations[self.destmap[fname]]
        if not os.path.exists(newdir):
          os.mkdir(newdir)
        newname = os.path.join(newdir, fname)
        # Avoid overwriting file.
        # TODO: something more sensible than crashing the program!
        if os.path.exists(newname):
          raise OSError("Avoided trashing file " + newname)
        else:
          os.rename(os.path.join(self.directory, fname), newname)
    sys.exit(0)

  def exitlist(self):
    self.writetext("Listing ...", (20, 180), (255, 255, 0))
    pygame.display.flip()
    for fname in self.filelist:
      if self.destmap[fname] != 0:
        newdir = self.destinations[self.destmap[fname]]
        newname = os.path.join(newdir, fname)
        print newname
    sys.exit(0)

  def go(self):
    """Main loop.  Reads events (mostly keystrokes) and handles them."""
    while True:
      event = pygame.event.wait()
      if event.type == pygame.QUIT:
        sys.exit()
      if event.type == pygame.KEYDOWN:
        if event.key == pygame.K_q and (event.mod & pygame.KMOD_SHIFT):
          self.bailout()   # exit on Shift-Q
        elif event.key == pygame.K_ESCAPE:
          self.bailout()   # exit on Escape
        elif event.key == pygame.K_s and (event.mod & pygame.KMOD_SHIFT):
          self.done()      # save and exit on shift-S
        elif event.key == pygame.K_l and (event.mod & pygame.KMOD_SHIFT):
          self.exitlist()  # exit with a filename list on shift-L
        elif event.key == pygame.K_SPACE:
          self.switchdest(self.filelist[self.current])
        elif event.key == pygame.K_RIGHT:
          if self.current < len(self.filelist) - 1:  self.current += 1
        elif event.key == pygame.K_LEFT:
          if self.current > 0:  self.current -= 1
        elif event.key == pygame.K_c:
          self.crosshair = (self.crosshair + 1) % 3
        elif event.key == pygame.K_v:
          self.verbose = (self.verbose + 1) % 3
      self.display(self.filelist[self.current])


if __name__ == '__main__':
  try:
    srcdir = sys.argv[1]
    destdirs = sys.argv[2:]
  except IndexError:
    # We didn't get enough args.  Print usage message and exit.
    print USAGE
    sys.exit(1)

  # Check all destinations for existence, directoriness, and permissions.
  # BUG: User still can specify a dir that doesn't currently exist, but
  #      is inside a dir that we don't have permissions to.
  for dest in destdirs:
    if os.path.exists(dest):
      if not os.path.isdir(dest):
        raise OSError("Not a directory: " + dest)
      if not os.access(dest, os.W_OK | os.X_OK):
        raise OSError("Not writeable: " + dest)

  # Start Pygame with a hardware accelerated screen.
  pygame.init()
  flags = (pygame.FULLSCREEN | pygame.HWSURFACE | pygame.DOUBLEBUF)
  screen = pygame.display.set_mode((0, 0), flags)

  s = Sorter(screen, srcdir, destdirs)
  s.go()


