from __future__ import print_function
from __future__ import absolute_import

from ..appearances import AppearanceBase, Appearance
from ..textures import TextureBase, SurfaceTexture, AutoTextureSource
from ..dircontext import defaultDirContext

from .. import settings

class TextureTilingMode(object):
    F_none = 0
    F_hash = 1

class TexturesDictionary(AppearanceBase):
    def __init__(self, textures, scale_factor=(1.0, 1.0), tiling=TextureTilingMode.F_none, shadow=None, context=defaultDirContext):
        AppearanceBase.__init__(self)
        self.textures = textures
        self.scale_factor = scale_factor
        self.tiling = tiling
        self.shadow = shadow
        self.srgb = settings.use_srgb
        self.nb_textures = 0
        for (name, texture) in self.textures.items():
            if texture is not None and not isinstance(texture, TextureBase):
                texture = SurfaceTexture(AutoTextureSource(texture, None, context), None, srgb=self.srgb)
            self.textures[name] = texture
            texture.set_target(False, "tex_" + name)
            self.nb_textures += 1

    def set_shadow(self, shadow):
        self.shadow = shadow

    def apply_textures(self, shape):
        for (name, texture) in self.textures.items():
            texture.apply(shape)

    def texture_loaded_cb(self, texture, patch, owner):
        owner.jobs_done_cb(None)

    def load_textures(self, shape, owner):
        for (name, texture) in self.textures.items():
            texture.load(shape, self.texture_loaded_cb, (shape, owner))

    def apply(self, shape, owner):
        if (shape.jobs & Appearance.JOB_TEXTURE_LOAD) == 0:
            #print("APPLY", shape, self.nb_textures)
            if self.nb_textures > 0:
                shape.jobs |= Appearance.JOB_TEXTURE_LOAD
                shape.jobs_pending += self.nb_textures
                self.load_textures(shape, owner)

class ProceduralAppearance(AppearanceBase):
    def __init__(self,
                 scale_factor = (1, 1),
                 shadow=None):
        AppearanceBase.__init__(self)
        self.shadow = shadow
        self.scale_factor = scale_factor

    def set_shadow(self, shadow):
        self.shadow = shadow
