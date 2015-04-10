#version 130

uniform float scale;
in vec4 color;
in vec2 position;
out vec4 v_color;

void main()
{
  gl_Position = vec4(scale*position, 0.0, 1.0);
  v_color = color;
}