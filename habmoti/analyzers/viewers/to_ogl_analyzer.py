import math
from threading import Lock
from typing import override, TYPE_CHECKING

import array
import numpy as np
from numpy.typing import NDArray

from .data_viewer_analyzer import DataViewerAnalyzer

if TYPE_CHECKING:
    from ..analyzer import Habmoti, FrameData
    from ...data.body_kinematics import BodyKinematics, BodyModel

_M_PI = 3.1415926


class ToOglAnalyzer(DataViewerAnalyzer):
    """
    Class that manages input events, window and OpenGL rendering pipeline
    """

    def __init__(self):
        self._is_started = False
        self._habmoti: Habmoti | None = None

        self._skeletons: list[_Skeleton] = []
        self._mutex = Lock()

        # Create the rendering camera
        self._projection = array.array("f")
        self._basic_sphere = _Simple3DObject(True)

        # Prepare internal elements
        self._window_id = None
        self._shader_sk_image: _Shader = None
        self._shader_sk_mvp = None
        self._shader_sk_color = None
        self._shader_sphere_image = None
        self._shader_sphere_mvp = None
        self._shader_sphere_color = None
        self._shader_sphere_pt = None

    @property
    @override
    def name(self) -> str:
        return "OpenGL Viewer"

    @override
    def initialize(self, habmoti: Habmoti):
        self._habmoti = habmoti

        _OGL.glut.glutInit()
        wnd_w = _OGL.glut.glutGet(_OGL.glut.GLUT_SCREEN_WIDTH)
        wnd_h = _OGL.glut.glutGet(_OGL.glut.GLUT_SCREEN_HEIGHT)
        width = int(wnd_w * 0.9)
        height = int(wnd_h * 0.9)

        _OGL.glut.glutInitWindowSize(width, height)
        # The window opens at the upper left corner of the screen
        _OGL.glut.glutInitWindowPosition(int(wnd_w * 0.05), int(wnd_h * 0.05))
        _OGL.glut.glutInitDisplayMode(_OGL.glut.GLUT_DOUBLE | _OGL.glut.GLUT_SRGB)
        self._window_id = _OGL.glut.glutCreateWindow(b"ZED Fusion Body Tracking")
        _OGL.gl.glViewport(0, 0, width, height)

        _OGL.glut.glutSetOption(_OGL.glut.GLUT_ACTION_ON_WINDOW_CLOSE, _OGL.glut.GLUT_ACTION_CONTINUE_EXECUTION)

        _OGL.gl.glEnable(_OGL.gl.GL_BLEND)
        _OGL.gl.glBlendFunc(_OGL.gl.GL_SRC_ALPHA, _OGL.gl.GL_ONE_MINUS_SRC_ALPHA)

        _OGL.gl.glEnable(_OGL.gl.GL_LINE_SMOOTH)
        _OGL.gl.glHint(_OGL.gl.GL_LINE_SMOOTH_HINT, _OGL.gl.GL_NICEST)
        _OGL.gl.glDisable(_OGL.gl.GL_DEPTH_TEST)

        _OGL.gl.glEnable(_OGL.gl.GL_FRAMEBUFFER_SRGB)

        # Compile and create the shader for 3D objects
        self._shader_sk_image = _Shader(self._vertex_shader(), self._fragment_shader())
        self._shader_sk_mvp = _OGL.gl.glGetUniformLocation(self._shader_sk_image.get_program_id(), "u_mvpMatrix")
        self._shader_sk_color = _OGL.gl.glGetUniformLocation(self._shader_sk_image.get_program_id(), "u_color")

        self._shader_sphere_image = _Shader(self._sphere_shader(), self._fragment_shader())
        self._shader_sphere_mvp = _OGL.gl.glGetUniformLocation(
            self._shader_sphere_image.get_program_id(), "u_mvpMatrix"
        )
        self._shader_sphere_color = _OGL.gl.glGetUniformLocation(self._shader_sphere_image.get_program_id(), "u_color")
        self._shader_sphere_pt = _OGL.gl.glGetUniformLocation(self._shader_sphere_image.get_program_id(), "u_pt")

        self._set_render_camera_projection(60, 0.1, 200)

        self._basic_sphere.add_sphere()
        self._basic_sphere.set_drawing_type(_OGL.gl.GL_QUADS)
        self._basic_sphere.push_to_gpu()

        # Register the drawing function with GLUT
        _OGL.glut.glutDisplayFunc(self._draw_callback)
        # Register the function called when nothing happens
        _OGL.glut.glutIdleFunc(self._idle)

        _OGL.glut.glutKeyboardFunc(self._key_pessed_callback)
        # Register the closing function
        _OGL.glut.glutCloseFunc(self.dispose)

        self._is_started = True

    @override
    def perform(self, frame_data: FrameData | None) -> None:
        if self._is_started and frame_data is not None:
            self._update_bodies(frame_data.body_kinematics)
        _OGL.glut.glutMainLoopEvent()

    @override
    def dispose(self):
        if self._habmoti is not None:
            self._habmoti.terminate()
        self._habmoti = None
        if self._is_started:
            self._is_started = False
        # Close the current window
        if self._window_id is not None:
            _OGL.glut.glutDestroyWindow(self._window_id)
            _OGL.glut.glutMainLoopEvent()
            self._window_id = None

    def _set_render_camera_projection(self, fov, _znear, _zfar):
        # Just slightly move up the ZED camera FOV to make a small black border
        fov_y = (fov + 0.5) * _M_PI / 180
        fov_x = (fov + 0.5) * _M_PI / 180

        im_w = 1280
        im_h = 720

        self._projection.append(1 / math.tan(fov_x * 0.5))  # Horizontal FoV.
        self._projection.append(0)
        # Horizontal offset.
        self._projection.append(2 * ((im_w * 0.5) / im_w) - 1)
        self._projection.append(0)

        self._projection.append(0)
        self._projection.append(1 / math.tan(fov_y * 0.5))  # Vertical FoV.
        # Vertical offset.
        self._projection.append(-(2 * ((im_h * 0.5) / im_h) - 1))
        self._projection.append(0)

        self._projection.append(0)
        self._projection.append(0)
        # Near and far planes.
        self._projection.append(-(_zfar + _znear) / (_zfar - _znear))
        # Near and far planes.
        self._projection.append(-(2 * _zfar * _znear) / (_zfar - _znear))

        self._projection.append(0)
        self._projection.append(0)
        self._projection.append(-1)
        self._projection.append(0)

    def _update_bodies(self, body_kinematics: BodyKinematics | None):  # _objs of type sl.Bodies
        self._mutex.acquire()

        # Clear objects
        self._skeletons.clear()
        # Only show tracked objects
        if body_kinematics is not None:
            for id, body in enumerate(body_kinematics.body_list):
                current_skeleton = _Skeleton(body_kinematics.body_model)
                current_skeleton.set(id, body)
                self._skeletons.append(current_skeleton)
        self._mutex.release()

    def _idle(self):
        if self._is_started:
            _OGL.glut.glutPostRedisplay()

    def _key_pessed_callback(self, key, x, y):
        if ord(key) == 113 or ord(key) == 27:
            self.dispose()

    def _draw_callback(self):
        if self._is_started:
            _OGL.gl.glClear(_OGL.gl.GL_COLOR_BUFFER_BIT | _OGL.gl.GL_DEPTH_BUFFER_BIT)

            self._mutex.acquire()
            self._update_skeletons()
            self._draw()
            self._mutex.release()

            _OGL.glut.glutSwapBuffers()
            _OGL.glut.glutPostRedisplay()

    def _update_skeletons(self):
        for body in self._skeletons:
            body.push_to_gpu()

    def _draw(self):
        _OGL.gl.glUseProgram(self._shader_sk_image.get_program_id())
        _OGL.gl.glUniformMatrix4fv(
            self._shader_sk_mvp, 1, _OGL.gl.GL_TRUE, (_OGL.gl.GLfloat * len(self._projection))(*self._projection)
        )

        _OGL.gl.glPolygonMode(_OGL.gl.GL_FRONT_AND_BACK, _OGL.gl.GL_FILL)
        for body in self._skeletons:
            body.draw_joint_links(self._shader_sk_color)
        _OGL.gl.glUseProgram(0)

        _OGL.gl.glUseProgram(self._shader_sphere_image.get_program_id())
        _OGL.gl.glUniformMatrix4fv(
            self._shader_sphere_mvp,
            1,
            _OGL.gl.GL_TRUE,
            (_OGL.gl.GLfloat * len(self._projection))(*self._projection),
        )
        for body in self._skeletons:
            body.draw_joint_centers(self._shader_sphere_color, self._basic_sphere, self._shader_sphere_pt)
        _OGL.gl.glUseProgram(0)

    @staticmethod
    def _sphere_shader() -> str:
        return """
        # version 330 core
        layout(location = 0) in vec3 in_Vertex;
        layout(location = 1) in vec3 in_Normal;
        out vec4 b_color;
        out vec3 b_position;
        out vec3 b_normal;
        uniform mat4 u_mvpMatrix;
        uniform vec4 u_color;
        uniform vec4 u_pt;
        void main() {
        b_color = u_color;
        b_position = in_Vertex;
        b_normal = in_Normal;
        gl_Position =  u_mvpMatrix * (u_pt + vec4(in_Vertex, 1));
        }
        """

    @staticmethod
    def _vertex_shader() -> str:
        return """
        # version 330 core
        layout(location = 0) in vec3 in_Vertex;
        layout(location = 1) in vec3 in_Normal;
        out vec4 b_color;
        out vec3 b_position;
        out vec3 b_normal;
        uniform mat4 u_mvpMatrix;
        uniform vec4 u_color;
        void main() {
        b_color = u_color;
        b_position = in_Vertex;
        b_normal = in_Normal;
        gl_Position =  u_mvpMatrix * vec4(in_Vertex, 1);
        }
        """

    @staticmethod
    def _fragment_shader() -> str:
        return """
        # version 330 core
        in vec4 b_color;
        in vec3 b_position;
        in vec3 b_normal;
        out vec4 out_Color;
        void main() {
            vec3 lightPosition = vec3(0, 2, 1);
            float ambientStrength = 0.3;
            vec3 lightColor = vec3(0.75, 0.75, 0.9);
            vec3 ambient = ambientStrength * lightColor;
            vec3 lightDir = normalize(lightPosition - b_position);
            float diffuse = (1 - ambientStrength) * max(dot(b_normal, lightDir), 0.0);
            out_Color = vec4(b_color.rgb * (diffuse + ambient), 1);
        }
        """


class _Shader:
    def __init__(self, _vs, _fs):
        self.program_id = _OGL.gl.glCreateProgram()
        vertex_id = self.compile(_OGL.gl.GL_VERTEX_SHADER, _vs)
        fragment_id = self.compile(_OGL.gl.GL_FRAGMENT_SHADER, _fs)

        _OGL.gl.glAttachShader(self.program_id, vertex_id)
        _OGL.gl.glAttachShader(self.program_id, fragment_id)
        _OGL.gl.glBindAttribLocation(self.program_id, 0, "in_vertex")
        _OGL.gl.glBindAttribLocation(self.program_id, 1, "in_texCoord")
        _OGL.gl.glLinkProgram(self.program_id)

        if _OGL.gl.glGetProgramiv(self.program_id, _OGL.gl.GL_LINK_STATUS) != _OGL.gl.GL_TRUE:
            info = _OGL.gl.glGetProgramInfoLog(self.program_id)
            if (self.program_id is not None) and (self.program_id > 0) and _OGL.gl.glIsProgram(self.program_id):
                _OGL.gl.glDeleteProgram(self.program_id)
            if (vertex_id is not None) and (vertex_id > 0) and _OGL.gl.glIsShader(vertex_id):
                _OGL.gl.glDeleteShader(vertex_id)
            if (fragment_id is not None) and (fragment_id > 0) and _OGL.gl.glIsShader(fragment_id):
                _OGL.gl.glDeleteShader(fragment_id)
            raise RuntimeError("Error linking program: %s" % (info))
        if (vertex_id is not None) and (vertex_id > 0) and _OGL.gl.glIsShader(vertex_id):
            _OGL.gl.glDeleteShader(vertex_id)
        if (fragment_id is not None) and (fragment_id > 0) and _OGL.gl.glIsShader(fragment_id):
            _OGL.gl.glDeleteShader(fragment_id)

    def compile(self, _type, _src):
        try:
            shader_id = _OGL.gl.glCreateShader(_type)
            if shader_id == 0:
                raise f"ERROR: shader type {_type} does not exist"

            _OGL.gl.glShaderSource(shader_id, _src)
            _OGL.gl.glCompileShader(shader_id)
            if _OGL.gl.glGetShaderiv(shader_id, _OGL.gl.GL_COMPILE_STATUS) != _OGL.gl.GL_TRUE:
                info = _OGL.gl.glGetShaderInfoLog(shader_id)
                if (shader_id is not None) and (shader_id > 0) and _OGL.gl.glIsShader(shader_id):
                    _OGL.gl.glDeleteShader(shader_id)
                raise RuntimeError("Shader compilation failed: %s" % (info))
            return shader_id
        except:
            if (shader_id is not None) and (shader_id > 0) and _OGL.gl.glIsShader(shader_id):
                _OGL.gl.glDeleteShader(shader_id)
            raise

    def get_program_id(self):
        return self.program_id


class _Simple3DObject:
    """
    Class that manages simple 3D objects to render with OpenGL
    """

    def __init__(self, _isStatic):
        self.vaoID = 0
        self.drawing_type = _OGL.gl.GL_TRIANGLES
        self.elementbufferSize = 0
        self.isStatic = _isStatic
        self.is_init = False

        self.vertices = array.array("f")
        self.normals = array.array("f")
        self.indices = array.array("I")

    def __del__(self):
        self.is_init = False
        if self.vaoID:
            self.vaoID = 0

    def add_vert(self, i_f, limit, height):
        p1 = [i_f, height, -limit]
        p2 = [i_f, height, limit]
        p3 = [-limit, height, i_f]
        p4 = [limit, height, i_f]

        self.add_line(p1, p2)
        self.add_line(p3, p4)

    """
    Add a unique point to the list of points
    """

    def add_pt(self, _pts):
        for pt in _pts:
            self.vertices.append(pt)

    """
    Add a unique normal to the list of normals
    """

    def add_normal(self, _normals):
        for normal in _normals:
            self.normals.append(normal)

    """
    Add a set of points to the list of points and their corresponding color
    """

    def add_points(self, _pts):
        for i in range(len(_pts)):
            pt = _pts[i]
            self.add_pt(pt)
            current_size_index = int((len(self.vertices) / 3)) - 1
            self.indices.append(current_size_index)
            self.indices.append(current_size_index + 1)

    """
    Add a point and its corresponding color to the list of points
    """

    def add_point_clr(self, _pt):
        self.add_pt(_pt)
        self.add_normal([0.3, 0.3, 0.3])
        self.indices.append(len(self.indices))

    def add_point_clr_norm(self, _pt, _norm):
        self.add_pt(_pt)
        self.add_normal(_norm)
        self.indices.append(len(self.indices))

    """
    Define a line from two points
    """

    def add_line(self, _p1, _p2):
        self.add_point_clr(_p1)
        self.add_point_clr(_p2)

    def add_sphere(self):
        m_radius = 0.025
        m_stack_count = 12
        m_sector_count = 12

        for i in range(m_stack_count + 1):
            lat0 = _M_PI * (-0.5 + (i - 1) / m_stack_count)
            z0 = math.sin(lat0)
            zr0 = math.cos(lat0)

            lat1 = _M_PI * (-0.5 + i / m_stack_count)
            z1 = math.sin(lat1)
            zr1 = math.cos(lat1)
            for j in range(m_sector_count):
                lng = 2 * _M_PI * (j - 1) / m_sector_count
                x = math.cos(lng)
                y = math.sin(lng)

                v = [m_radius * x * zr0, m_radius * y * zr0, m_radius * z0]
                normal = [x * zr0, y * zr0, z0]
                self.add_point_clr_norm(v, normal)

                v = [m_radius * x * zr1, m_radius * y * zr1, m_radius * z1]
                normal = [x * zr1, y * zr1, z1]
                self.add_point_clr_norm(v, normal)

                lng = 2 * _M_PI * j / m_sector_count
                x = math.cos(lng)
                y = math.sin(lng)

                v = [m_radius * x * zr1, m_radius * y * zr1, m_radius * z1]
                normal = [x * zr1, y * zr1, z1]
                self.add_point_clr_norm(v, normal)

                v = [m_radius * x * zr0, m_radius * y * zr0, m_radius * z0]
                normal = [x * zr0, y * zr0, z0]
                self.add_point_clr_norm(v, normal)

    def push_to_gpu(self):
        if self.is_init == False:
            self.vboID = _OGL.gl.glGenBuffers(3)
            self.is_init = True

        draw_type = _OGL.gl.GL_DYNAMIC_DRAW
        if self.isStatic:
            draw_type = _OGL.gl.GL_STATIC_DRAW

        if len(self.vertices):
            _OGL.gl.glBindBuffer(_OGL.gl.GL_ARRAY_BUFFER, self.vboID[0])
            _OGL.gl.glBufferData(
                _OGL.gl.GL_ARRAY_BUFFER,
                len(self.vertices) * self.vertices.itemsize,
                (_OGL.gl.GLfloat * len(self.vertices))(*self.vertices),
                draw_type,
            )

        if len(self.normals):
            _OGL.gl.glBindBuffer(_OGL.gl.GL_ARRAY_BUFFER, self.vboID[1])
            _OGL.gl.glBufferData(
                _OGL.gl.GL_ARRAY_BUFFER,
                len(self.normals) * self.normals.itemsize,
                (_OGL.gl.GLfloat * len(self.normals))(*self.normals),
                draw_type,
            )

        if len(self.indices):
            _OGL.gl.glBindBuffer(_OGL.gl.GL_ELEMENT_ARRAY_BUFFER, self.vboID[2])
            _OGL.gl.glBufferData(
                _OGL.gl.GL_ELEMENT_ARRAY_BUFFER,
                len(self.indices) * self.indices.itemsize,
                (_OGL.gl.GLuint * len(self.indices))(*self.indices),
                draw_type,
            )

        self.elementbufferSize = len(self.indices)

    def clear(self):
        self.vertices = array.array("f")
        self.normals = array.array("f")
        self.indices = array.array("I")

    def set_drawing_type(self, _type):
        self.drawing_type = _type

    def draw(self):
        if (self.elementbufferSize > 0) and self.is_init:
            _OGL.gl.glEnableVertexAttribArray(0)
            _OGL.gl.glBindBuffer(_OGL.gl.GL_ARRAY_BUFFER, self.vboID[0])
            _OGL.gl.glVertexAttribPointer(0, 3, _OGL.gl.GL_FLOAT, _OGL.gl.GL_FALSE, 0, None)

            _OGL.gl.glEnableVertexAttribArray(1)
            _OGL.gl.glBindBuffer(_OGL.gl.GL_ARRAY_BUFFER, self.vboID[1])
            _OGL.gl.glVertexAttribPointer(1, 3, _OGL.gl.GL_FLOAT, _OGL.gl.GL_FALSE, 0, None)

            _OGL.gl.glBindBuffer(_OGL.gl.GL_ELEMENT_ARRAY_BUFFER, self.vboID[2])
            _OGL.gl.glDrawElements(self.drawing_type, self.elementbufferSize, _OGL.gl.GL_UNSIGNED_INT, None)

            _OGL.gl.glDisableVertexAttribArray(0)
            _OGL.gl.glDisableVertexAttribArray(1)


class _Skeleton:
    def __init__(self, body_model: BodyModel):
        self._segment_links = body_model.segment_links()
        self._clr: list[float] = [0.0, 0.0, 0.0, 1.0]
        self._joint_positions: list[np.ndarray] = []
        self._joint_links = _Simple3DObject(False)
        self._Z: float = 1.0

    def set(self, id: int, data: NDArray[np.float64]):
        self._joint_links.set_drawing_type(_OGL.gl.GL_LINES)
        self._clr = self._generate_color_id(id)
        # Draw skeletons
        self._createSkeleton(data)

    def draw_joint_centers(self, shader_clr, sphere, shader_pt):
        _OGL.gl.glUniform4f(shader_clr, self._clr[0], self._clr[1], self._clr[2], self._clr[3])
        for k in self._joint_positions:
            _OGL.gl.glUniform4f(shader_pt, k[0], k[1], k[2], 1)
            sphere.draw()

    def draw_joint_links(self, shader_sk_clr):
        _OGL.gl.glUniform4f(shader_sk_clr, self._clr[0], self._clr[1], self._clr[2], self._clr[3])
        _OGL.gl.glLineWidth((20.0 / self._Z))
        self._joint_links.draw()

    def push_to_gpu(self):
        self._joint_links.push_to_gpu()

    def _createSkeleton(self, data: NDArray[np.float64]):
        self._joint_positions = data
        self._joint_links.clear()
        for bone1_index, bone2_index in self._segment_links:
            kp_1 = data[bone1_index.value, :3]
            kp_2 = data[bone2_index.value, :3]
            if math.isfinite(kp_1[0]) and math.isfinite(kp_2[0]):
                self._joint_links.add_line(kp_1, kp_2)

    @staticmethod
    def _generate_color_id_u(idx):
        arr = []
        if idx < 0:
            arr = [236, 184, 36, 255]
        else:
            colors = [(232, 176, 59), (175, 208, 25), (102, 205, 105), (185, 0, 255), (99, 107, 252)]
            color_idx = idx % len(colors)
            arr = [colors[color_idx][0], colors[color_idx][1], colors[color_idx][2], 255]
        return arr

    @staticmethod
    def _generate_color_id(_idx):
        clr = np.divide(_Skeleton._generate_color_id_u(_idx), 255.0)
        clr[0], clr[2] = clr[2], clr[0]
        return clr


class _OGLMeta(type):
    _loaded = False

    def _load(cls):
        if cls._loaded:
            return

        try:
            import OpenGL.GL as gl
            import OpenGL.GLU as glu
            import OpenGL.GLUT as glut
        except ImportError as e:
            raise ImportError(
                "PyOpenGL is not installed. " "Install with: pip install PyOpenGL PyOpenGL_accelerate"
            ) from e

        cls.gl = gl
        cls.glu = glu
        cls.glut = glut
        cls._loaded = True

    def __getattr__(cls, name):
        if name in {"gl", "glu", "glut"}:
            cls._load()
            return getattr(cls, name)
        raise AttributeError(name)


class _OGL(metaclass=_OGLMeta):
    pass
