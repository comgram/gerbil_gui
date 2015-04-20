#version 120

//uniform float scale;
uniform mat4 mvp_matrix;
//uniform mat4 view;
//uniform mat4 proj;

attribute vec4 color;
attribute vec2 position;
varying vec4 v_color;

void main()
{
  //gl_Position = proj * view * model * vec4(position, 0.0, 1.0);
  gl_Position = mvp_matrix * vec4(position / 1000, 0.0, 1.0);
  v_color = color;
}