#
#   Imposter maker for Second Life
#
#   John Nagle
#   August, 2018.
#
#   License: GPLv3
#
#   System for taking a set of images taken in Second Life and 
#   turning them into a properly aligned and measured texture for
#   a billboard impostor.
#
#   Images must be surrounded by a solid-color frame and should be backed
#   by a solid-color background. The images will be cropped to the frame
#   and the solid color background will be made transparent.
#
#   All the images are combined into one texture image, which is a power of
#   2 in size in both dimensions.
#
#
import argparse
import glob
import PIL
import PIL.Image
import impostorfile

def stringcommon(a,b) :
    '''
    Returns number of characters a and b have in common
    from the beginning
    '''
    cnt = min(len(a),len(b))
    for i in range (cnt) :
        if not a[i] == b[i] :
            return(i)               # number of chars in common
    return(cnt)
    
def stringscommon(lst) :
    '''
    Given a list of strings, return the portion of
    the string common to all
    '''
    if len(lst) == 0 :
        return None
    cnt = min([stringcommon(lst[0],s) for s in lst])
    return lst[0][0:cnt]


class Impostor :

    #   Constructor
    def __init__(self, args) :
        self.options = args
        print("File args: ", args.files)                # ***TEMP***
        self.filenames = args.files
        self.framesize = (args.width, args.height)      # size of image frame in meters
        self.impostorfiles = []                         # impostor file object
        self.croprect = None                            # cropping rectangle for all images 
        self.sizes = None                               # sizes of all images (pixels) before final crop
        
    #   Read in all files
    def readfiles(self) :
        for name in self.filenames :
            ifile = impostorfile.ImpostorFile(self, name)            # object for this input image
            ifile.readimage()                           # read the image
            self.impostorfiles.append(ifile)            # accumulate image objects
            
    def processfiles(self) :
        for impf in self.impostorfiles :                # for all files
            valid = impf.extract()                      # extract useful part of file
            if not valid :
                return False                            # failed
        return True                                     # success
        
    def outfilename(self, name=None) :
        '''
        Generate output file name
        
        Default uses the common part of all the input file names,
        including the directory.
        '''
        if name is None :
            s = stringscommon(self.filenames)
            sparts = s.split('/')
            sparts[-1] = "impostor-" + sparts[-1]
            s = '/'.join(sparts)
        else :
            s = name
        return s + ".png"
        
    def calcimpostorsize(self) :
        '''
        Calculate size of final impostor object in meters.
        
        self.sizes represents the pixel size of a rectangle whose dimensions are framesize.
        '''
        metersperpixel = (self.framesize[0] / self.sizes[0], self.framesize[1] / self.sizes[1])  # meters per pixel
        croppedsize = (self.croprect[2] - self.croprect[0], self.croprect[3] - self.croprect[1]) # size of cropped image
        ####reductionratio = (croppedsize[0] / self.sizes[0], croppedsize[1] / self.sizes[1]) # reduced size of cropped version
        ####finalsizeold = (reductionratio[0]*self.framesize[0], reductionratio[1]*self.framesize[1]) # size of actual impostor in meters
        finalsize = (metersperpixel[0]*croppedsize[0], metersperpixel[1]*croppedsize[1])    # size of image after cropping
        print("Cropped size in pixels: ", croppedsize, "  Frame size (m): ", self.framesize, "  Frame size (px):", self.sizes)    # ***TEMP***
        ####print("Old final size: ", finalsizeold, "  New final size: ", finalsize)
        return finalsize
                
    def uniformcrop(self) :
        '''
        Calculate the cropping rectangle for all impostors.
        
        This is the rectangle which contains all the bounding boxes of
        all the images, and also is centered in X.
        
        Must also look at the size of each image. All images should be
        very close to the same size. If they are not, we have a problem.
        '''
        bboxes = [impf.croppedbbox for impf in self.impostorfiles] # all bboxes
        #   Size check. All cropped images must be close in size
        MAXALLOWEDSIZEMISMATCH = 0.05                   # allow 5% variation
        sizes = [impf.croppedimage.size for impf in self.impostorfiles] # all sizes
        maxwidth = max([s[0] for s in sizes])
        maxheight = max([s[1] for s in sizes])
        for s in sizes :
            if ((maxwidth - s[0]) / maxwidth > MAXALLOWEDSIZEMISMATCH or 
                (maxheight - s[1]) / maxheight > MAXALLOWEDSIZEMISMATCH) :
                print("Sizes of images inside frame vary too much.")
                return False
        self.sizes = (maxwidth, maxheight)              # size info for aspect ratio calc    
        #   Compute initial crop rectangle
        wrect = (min([b[0] for b in bboxes]),
            min([b[1] for b in bboxes]), 
            max([b[2] for b in bboxes]), 
            max([b[3] for b in bboxes]))
        xcenter = int(maxwidth/2)                       # center of X dimension
        xleftsize = max(0,xcenter-wrect[0])             # limits of X relative to center
        xrightsize = min(maxwidth,wrect[2]-xcenter)
        xhalfsize = max(xleftsize, xrightsize)          # width relative to center
        self.croprect = (xcenter - xhalfsize, wrect[1], xcenter + xhalfsize, wrect[3]) # actual cropping rectangle
        print("Final cropping rectangle: ",self.croprect)   # ***TEMP***
        croppedimages = [impf.croppedimage.crop(self.croprect) for impf in self.impostorfiles]    # crop all images
        self.croppedimages = croppedimages              # save cropped images
        for img in croppedimages :
            img.show()                                  # ***TEMP***
        return True
        
    def generateimpostor(self, imagesize) :
        '''
        Generate composite impostor image with each image
        adjusted to the indicated size.  Images are stacked
        vertically.
        '''
        cnt = len(self.croppedimages)                       # number of images to assemble
        composite = PIL.Image.new("RGBA", (imagesize[0], imagesize[1]*cnt)) # working image
        for n in range(cnt) :                               # for each image 
            resized = self.croppedimages[n].resize(imagesize,PIL.Image.LANCZOS)  # resize image to fit
            composite.paste(resized,(0,imagesize[1]*n))     # add to composite
        return composite                                    # return complete impostor image       

def parseargs() :
     #  Parse command line options
     parser = argparse.ArgumentParser(description="Second Life impostor generator")                 # usual argument parser
     parser.add_argument("--width", dest="width", metavar="W", type=float, default=6.0, help="Width of image frame in meters")
     parser.add_argument("--height", dest="height", metavar="H", type=float, default=3.0, help="Width of image frame in meters")
     parser.add_argument("--rez", dest="rez", metavar="OUTPUTWIDTH", type=int, default=64, help="Width of each output image in pixels.")
     parser.add_argument("--faces", dest="faces", metavar="N", default="8", help="Total faces, including top and bottom.")
     parser.add_argument("--form", dest="form", metavar="FORMNAME", default="STAR", help="STAR = N faces in a star pattern. TSTAR: Star plus top and bottom.")
     parser.add_argument("-v", "--verbose", action="store_true", dest="verbose", default=False, help="Verbose mode")
     parser.add_argument("files", nargs='+')
     args = parser.parse_args()
     #  Option validation
     return args


     
#   Main program
def main() :
    args = parseargs()                              # parse and check options
    imp = Impostor(args)                            # create main impostor object
    imp.readfiles()                                 # read in all images
    outfile = imp.outfilename()
    print("Will create ",outfile)
    valid = imp.processfiles()
    if not valid :
        print("Process files failed.")
        return False
    valid = imp.uniformcrop()
    if not valid :
        print("Uniform crop failed.")
        return False
    finalimage = imp.generateimpostor((128,64))    # ***TEMP***
    finalimage.show()
    print("Final impostor size (meters): %1.3f, %1.3f" % imp.calcimpostorsize()) # show final size in meters
    print("Creating ",outfile)
    finalimage.save(outfile)                        # Generate output file
    ####finalimage.save("/tmp/composite.png")           # ***TEMP***


     
#   Run program
main()
