#
#This file is part of Cosmonium.
#
#Copyright (C) 2018-2019 Laurent Deru.
#
#Cosmonium is free software: you can redistribute it and/or modify
#it under the terms of the GNU General Public License as published by
#the Free Software Foundation, either version 3 of the License, or
#(at your option) any later version.
#
#Cosmonium is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#GNU General Public License for more details.
#
#You should have received a copy of the GNU General Public License
#along with Cosmonium.  If not, see <https://www.gnu.org/licenses/>.
#

from __future__ import print_function
from __future__ import absolute_import

from .shapes import ShapeObject
from panda3d.core import NodePath
from cosmonium.shadows import SphereShadowCaster

class SurfaceCategory(object):
    def __init__(self, name):
        self.name = name

class SurfaceCategoryDB(object):
    def __init__(self):
        self.categories = {}

    def add(self, category):
        self.categories[category.name] = category

    def get(self, name):
        return self.categories.get(name)

surfaceCategoryDB = SurfaceCategoryDB()

class Surface(ShapeObject):
    def __init__(self, name=None, category=None, resolution=None, attribution=None, shape=None, appearance=None, shader=None, clickable=True):
        ShapeObject.__init__(self, name, shape, appearance, shader, clickable)
        self.category = category
        self.resolution = resolution
        self.attribution = attribution
        #TODO: parent is set to None when component is removed, so we use owner until this is done a better way...
        self.owner = None

    def get_component_name(self):
        return 'Surface'

    def is_flat(self):
        return False

    def create_shadows(self):
        if self.shape is not None and self.shape.is_spherical():
            self.shadow_caster = SphereShadowCaster(self.owner)
        else:
            self.shadow_caster = None

    def get_average_radius(self):
        return self.owner.get_apparent_radius()

    def get_min_radius(self):
        return self.owner.get_apparent_radius()

    def get_max_radius(self):
        return self.owner.get_apparent_radius()

    def global_to_shape_coord(self, x, y):
        return self.shape.global_to_shape_coord(x, y)

    def get_height_at(self, x, y):
        raise NotImplementedError

    def get_height_patch(self, patch, u, v):
        raise NotImplementedError

    def get_normals_at(self, x, y):
        coord = self.shape.global_to_shape_coord(x, y)
        return self.shape.get_normals_at(coord)

class FlatSurface(Surface):
    def is_flat(self):
        return True

    def get_height_at(self, x, y):
        return self.owner.get_apparent_radius()

    def get_height_patch(self, patch, u, v):
        return self.owner.get_apparent_radius()

class MeshSurface(Surface):
    def get_height_at(self, x, y):
        coord = self.shape.global_to_shape_coord(x, y)
        return self.shape.get_height_at(coord)

    def get_height_patch(self, patch, u, v):
        return self.shape.get_height_patch(patch, u, v)

class ProceduralSurface(FlatSurface):
    JOB_HEIGHTMAP = 0x0002
    def __init__(self, name, shape, heightmap, appearance, shader, clickable=True):
        FlatSurface.__init__(self, name, shape=shape, appearance=appearance, shader=shader, clickable=clickable)
        self.heightmap = heightmap
        self.biome = None

    def set_heightmap(self, heightmap):
        self.heightmap = heightmap

    def heightmap_ready_cb(self, heightmap, patch):
        if self.shape.patchable:
            self.jobs_done_cb(patch)
        else:
            self.jobs_done_cb(None)

    def schedule_patch_jobs(self, patch):
        if (patch.jobs & ProceduralSurface.JOB_HEIGHTMAP) == 0:
            #print("UPDATE", patch.str_id())
            patch.jobs |= ProceduralSurface.JOB_HEIGHTMAP
            patch.jobs_pending += 1
            if self.biome is not None:
                patch.jobs_pending += 1
            self.heightmap.create_heightmap(patch, self.heightmap_ready_cb, [patch])
            if self.biome is not None:
                self.biome.create_heightmap(patch, self.heightmap_ready_cb, [patch])
        FlatSurface.schedule_patch_jobs(self, patch)

    def schedule_shape_jobs(self, shape):
        if not shape.patchable:
            if (self.shape.jobs & ProceduralSurface.JOB_HEIGHTMAP) == 0:
                #print("UPDATE SHAPE", self.shape.str_id())
                self.shape.jobs |= ProceduralSurface.JOB_HEIGHTMAP
                self.shape.jobs_pending += 1
                if self.biome is not None:
                    self.shape.jobs_pending += 1
                self.heightmap.create_heightmap(self.shape, self.heightmap_ready_cb, [self.shape])
                if self.biome is not None:
                    self.biome.create_heightmap(self.shape, self.heightmap_ready_cb, [self.shape])
        FlatSurface.schedule_shape_jobs(self, shape)

class HeightmapSurface(ProceduralSurface):
    def __init__(self, name, radius, shape, heightmap, biome, appearance, shader, scale = 1.0, clickable=True, displacement=True, average=False):
        ProceduralSurface.__init__(self, name, shape, heightmap, appearance, shader, clickable)
        if radius != 0.0:
            self.height_scale = radius
        else:
            self.height_scale = 1.0
        if heightmap.median:
            self.min_radius = radius - self.height_scale * self.heightmap.height_scale
            self.max_radius = radius + self.height_scale * self.heightmap.height_scale
            self.radius = radius
            self.heightmap_base = radius
        else:
            self.min_radius = radius
            self.max_radius = radius + self.height_scale * self.heightmap.height_scale
            self.radius = radius + 0.5 * self.height_scale * self.heightmap.height_scale
            self.heightmap_base = radius
        self.biome = biome
        self.scale = scale
        self.displacement = displacement
        self.average = average
        #TODO: Make a proper method for this...
        shape.face_unique = True
        shape.set_heightmap(heightmap)

    def get_average_radius(self):
        return self.radius

    def get_min_radius(self):
        return self.min_radius

    def get_max_radius(self):
        return self.max_radius

    def global_to_shape_coord(self, x, y):
        return self.shape.global_to_shape_coord(x, y)

    def get_height(self, position):
        #TODO: Surface coord should be 0-1, not scaled
        x = position[0] / self.scale
        y = position[1] / self.scale
        return self.get_height_at(x, y)

    def get_height_at(self, x, y, strict=False):
        #print("get_height_at", x, y)
        if not self.displacement:
            return self.radius
        coord = self.shape.global_to_shape_coord(x, y)
        patch = self.shape.find_patch_at(coord)
        if patch is not None:
            heightmap_patch = self.heightmap.get_heightmap(patch)
        while patch is not None and (heightmap_patch is None or not heightmap_patch.heightmap_ready):
            patch = patch.parent
            if patch is not None:
                heightmap_patch = self.heightmap.get_heightmap(patch)
        if patch is not None:
            uv = patch.coord_to_uv(coord)
            #print("uv", uv)
            return self.get_height_patch(patch, *uv)
        elif strict:
            return None
        else:
            #print("Patch not found for", x, y)
            return self.radius

    def get_height_patch(self, patch, u, v, recursive=False):
        if not self.displacement:
            return self.radius
        heightmap = self.heightmap.get_heightmap(patch)
        while heightmap is None and patch is not None:
            print("Recurse")
            patch = patch.parent
            heightmap = self.heightmap.get_heightmap(patch)
            u /= 2.0
            v /= 2.0
        if heightmap is None:
            print("No heightmap")
            return self.radius
        if self.average:
            h = heightmap.get_average_height_uv(u, v)
        else:
            h = heightmap.get_height_uv(u, v)
        height = h * self.height_scale + self.heightmap_base
        return height
