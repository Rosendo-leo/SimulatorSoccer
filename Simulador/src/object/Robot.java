package object;

import java.awt.Color;
import java.awt.Graphics;
import java.awt.image.BufferedImage;

public class Robot extends Object{
	
	private String tag;
	private double maxSpeed, speed;
	private int startAngle;
	private Color time;
	private int Angle;
	
	public int i = 1;
	public int e = 1;

	public Robot(int x, int y, int diam, Color color, String tag, double maxSpeed) {
		super(x, y, diam, color);
		this.tag = tag;
		this.maxSpeed = maxSpeed;
		
		if(tag == "i") { //Adversário
			startAngle = -30;
			time = color.red;
		}
		if(tag == "r") {
			startAngle = 150;
			time = color.blue;
		}
	}
	
	public void tick() {
		//Angle++;
		velocity(255,0);
		if(tag == "i") { //Adversário
		}
	}
	
	public void velocity(int velX, int velY) {
		walkY((int)(velY*Math.cos(Angle)*0.003921568627451)+(int)(velY*Math.sin(Angle)*0.003921568627451));
		walkX((int)(velX*Math.sin(Angle)*0.003921568627451)+(int)(velX*Math.cos(Angle)*0.003921568627451));
	}
	
	public void walkX(int value) {
		if(this.getX()+speed < 1215-(diam/2) && this.getX()-speed > 0+(diam/2)) {
			this.setX((int)(getX()+(speed*value)));
		}
	}
	
	public void walkY(int value) {
		if(this.getY()+speed < 910-(diam/2) && this.getY()-speed > 0+(diam/2)) {
			this.setY((int)(getY()+(speed*value)));
		}
	}
	
	public void render(Graphics g) {
		super.render(g);
		g.setColor(color);
		g.fillOval(getX()-(diam/2), getY()-(diam/2), diam, diam);
		g.setColor(time);
		g.fillArc(getX()-(diam/2), getY()-(diam/2), diam, diam, startAngle+Angle, 60);
	}
}
