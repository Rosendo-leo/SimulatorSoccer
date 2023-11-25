package object;

import java.awt.Color;
import java.awt.Graphics;

public class Ball extends Object{

	public Ball(int x, int y, int diam, Color color) {
		super(x, y, diam, color);
	}
	
	public void tick(){
		
	}
	
	public void render(Graphics g) {
		super.render(g);
		g.setColor(color);
		g.fillOval(getX()-(diam/2), getY()-(diam/2), diam, diam);
	}
}
