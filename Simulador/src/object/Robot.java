package object;

import java.awt.Color;
import java.awt.Graphics;
import java.awt.image.BufferedImage;

import main.Simulator;

public class Robot extends Object{
	
	private String tag;
	private double maxSpeed, speed;
	private int startAngle;
	private Color time;
	public static int Angle;
	private int kAngle;
	
	public int speedX, speedY;
	
	public int i = 1;
	public int e = 1;

	public Robot(int x, int y, int diam, Color color, String tag, double maxSpeed) {
		super(x, y, diam, color);
		this.tag = tag;
		this.maxSpeed = maxSpeed;
		
		if(tag == "i") { //Adversário
			startAngle = -30;
			time = color.red;
			kAngle = 1;
			speed = maxSpeed;
		}
		if(tag == "r") { //Companheiro
			startAngle = 150;
			time = color.blue;
			kAngle = -1;
			speed = maxSpeed;
		}
	}
	
	public void tick() {
		//Angle++;
		velocity(1,1);
		Angle = kAngle*(int)(angleBall());
		if(tag == "i") { //Adversário
		}
		if(tag == "r") { //Companheiro		
		}
	}
	
	public double angleBall() {
		return Math.atan2(this.getY()-Simulator.ball.getY(),this.getX()-Simulator.ball.getX())*180/Math.PI;
	}
	
	public void velocity(int velX, int velY) {
		walkX(-kAngle*(Math.cos(Angle)*velX)+(Math.sin(Angle)*velX));
		walkY(kAngle*(Math.cos(Angle)*velY)+(Math.sin(Angle)*velY));
	}
	
	public void walkX(double value) {
		if(this.getX()+speed < 1215-(diam/2) && this.getX()-speed > 0+(diam/2)) {
			speedX = (int)(speed*value);
			this.setX(getX()+speedX);
		}
	}
	
	public void walkY(double value) {
		if(this.getY()+speed < 910-(diam/2) && this.getY()-speed > 0+(diam/2)) {
			speedY = (int)(speed*value);
			this.setY(getY()+speedY);
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
