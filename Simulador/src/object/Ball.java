package object;

import java.awt.Color;
import java.awt.Graphics;

import main.Simulator;

public class Ball extends Object{
	
	private double speed = 2;
	public int speedX, speedY;
	public boolean colin;

	public Ball(int x, int y, int diam, Color color) {
		super(x, y, diam, color);
	}
	
	public void tick(){
		//isRobot();
		//walkX(0);
		//walkY(0);
	}
	public void isRobot() {
		for(int i = 0; i < Simulator.objects.size(); i++)  {
			Object atual = Simulator.objects.get(i);
			if(atual instanceof Robot) {
				if(Object.isColliding(this, atual)) {
					colin = true;
					speedX = ((Robot) atual).speedX;
					speedY = ((Robot) atual).speedY;
				}else {
					colin = false;
				}
			}
		}
	}
	
	public void walkX(double value) {
		if(this.getX()+speed < 1215-(diam/2) && this.getX()-speed > 0+(diam/2)) {
			if(!colin)speedX = (int)(speed*value);
			this.setX(getX()+speedX);
		}
	}
	
	public void walkY(double value) {
		if(this.getY()+speed < 910-(diam/2) && this.getY()-speed > 0+(diam/2)) {
			if(!colin)speedY = (int)(speed*value);
			this.setY(getY()+speedY);
		}
	}
	
	public void render(Graphics g) {
		super.render(g);
		g.setColor(color);
		g.fillOval(getX()-(diam/2), getY()-(diam/2), diam, diam);
	}
}
