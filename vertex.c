#version 120

uniform float zoom;
uniform mat4 mat_m;
uniform mat4 mat_v;
uniform mat4 mat_p;
//uniform mat4 view;
//uniform mat4 proj;

attribute vec4 color;
attribute vec3 position;
varying vec4 v_color;

void main()
{
  //gl_Position = proj * view * model * vec4(position, 0.0, 1.0);
  gl_Position = mat_p * mat_v * mat_m * vec4(position, 1.0);
  v_color = color;
}