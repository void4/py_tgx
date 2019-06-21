from PIL import Image

def b2i(b):
	return int.from_bytes(b, byteorder='little', signed=True) 

def toint(b):
	return int.from_bytes(b, byteorder='little', signed=False) 

def i2b(i, length=1, signed=False, byteorder="little"):
	return int.to_bytes(i, length=length, byteorder=byteorder, signed=signed)

COLOR_MASK_BLUE = 0x001F
COLOR_MASK_GREEN = 0x03E0
COLOR_MASK_RED = 0x7C00

OPT_PIXELSTREAM = 0
OPT_NEWLINE = 4
OPT_PIXREPEAT = 2
OPT_TRANSPARENT = 1

class TGX:
	def __init__(self, path):
	
		if path.lower().endswith(".tgx"):
			with open(path, "rb") as f:
				self.bytes = f.read()
			
			self.index = 0
			self.header()
			
			while self.index < len(self.bytes):
				self.token()
		else:
			self.img = Image.open(path)
		
	def r(self, n):
		ret = self.bytes[self.index:self.index+n]
		self.index += n
		return ret
		
	def header(self):
		self.width = b2i(self.r(2))
		self.r(2)
		self.height = b2i(self.r(2))
		self.r(2)
		
		self.img = Image.new("RGBA", (self.width, self.height), color=(0,0,0,0))
		self.x = 0
		self.y = 0
		
	
	def rgb(self, twobytes):
		#green = (((twobytes[0]>>5)&0b111)<<5) | ((twobytes[1]&0b11)<<3)
		#blue = (twobytes[1]&0b11111)<<3
		#unknown = (twobytes[1]>>7)&0b1
		#red = ((twobytes[1]>>2)&0b11111)<<3
		v = toint(twobytes)
		blue = ((COLOR_MASK_BLUE & v) << 3)  & 0xff
		green = ((COLOR_MASK_GREEN & v) >> 2) & 0xff
		red = ((COLOR_MASK_RED & v) >> 7) & 0xff
		alpha = 255
		return (red, green, blue, alpha)
	
	def pix(self, color):
		try:
			self.img.putpixel((self.x, self.y), color)
		except IndexError as e:
			print(e)
			return
		self.x = (self.x + 1) % self.width
	
	def token(self):
		header = self.r(1)
		option = (header[0] >> 5) & 0b111
		bits = (header[0] & 0b11111) + 1
		#print(option, bits)
		if option == OPT_PIXELSTREAM:
			for i in range(bits):
				self.pix(self.rgb(self.r(2)))
		elif option == OPT_NEWLINE:
			self.y += 1
			self.x = 0
		elif option == OPT_PIXREPEAT:
			pixel = self.rgb(self.r(2))
			for i in range(bits):
				self.pix(pixel)
		elif option == OPT_TRANSPARENT:
			for i in range(bits):
				self.x += 1
		else:
			raise ValueError("unknown token option", option)
	
	def fromrgb(self, rgb):
		blue = rgb[2] >> 3
		green = (rgb[1] >> 3) << 5
		red = (rgb[0]>>3) << 10
		return i2b(red | green | blue, 2, False, "little")
	
	def save(self, path):
	
		header = i2b(self.img.width, 2) + i2b(0,2) + i2b(self.img.height, 2) + i2b(0,2)
	
		tokens = b""
		
		p = 0
		total = self.img.width*self.img.height
		
		x = y = 0
		
		iscolor = True
		
		tokendata = b""
		tokensize = 0
		
		def writePixels():
			nonlocal tokendata, tokensize, tokens
			if tokensize > 0:
				#print(tokensize, iscolor)
				if iscolor:
					if all(e==tokendata[0] for e in tokendata):
						# TODO not correct yet, have to check every two bytes
						tokenheader = i2b((OPT_PIXREPEAT << 5) | (tokensize-1), 1, False)
						tokendata = tokendata[:2]
					else:
						tokenheader = i2b((OPT_PIXELSTREAM << 5) | (tokensize-1), 1, False)
					tokens += tokenheader + tokendata
					tokendata = b""
					tokensize = 0
				else:
					tokenheader = i2b((OPT_TRANSPARENT << 5) | (tokensize-1), 1, False)
					tokens += tokenheader
					tokensize = 0
		
		while p<total:
			try:
				pixel = self.img.getpixel((x,y))
			except IndexError as e:
				print(e)
				break
			p += 1
			x = (x+1)%self.img.width
			if tokensize==32:
				writePixels()

			if pixel[3] == 0:
				if iscolor:
					writePixels()
				iscolor = False
				tokensize += 1
			else:
				if not iscolor:
					writePixels()
				iscolor = True
				tokensize += 1
				tokendata += self.fromrgb(pixel)
			
			if x == self.img.width-1:
				writePixels()
				tokenheader = i2b(OPT_NEWLINE << 5, 1, False)
				tokens += tokenheader
				y += 1
				#x = 0
	
		bytes = header + tokens
	
		with open(path, "wb+") as f:
			f.write(bytes)

if __name__ == "__main__":
	name = "ST74_Tower1"
	
	if False:
		tgx = TGX(name+".tgx")
		tgx.img.save(name+".png")
	
	else:
		tgx = TGX(name+".png")
		tgx.save(name+".tgx")

	if False:	
		from glob import glob
		import os

		for path in glob("gfx/*.tgx")[:10]:
			tgx = TGX(path)
			print(path, tgx.width, tgx.height)
			#tgx.img.show()
			filename = os.path.split(path)[-1]
			newfilename = filename.rsplit(".",1)[0]+".png"
			imgoutpath = os.path.join("out", newfilename)
			tgx.img.save(imgoutpath)
			
			outpath = os.path.join("gfx2", filename)
			tgx.save(outpath)
			
			tgx2 = TGX(outpath)
			img2outpath = os.path.join("out2", newfilename)
			tgx2.img.save(img2outpath)
