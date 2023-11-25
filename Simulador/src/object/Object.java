package object;

import java.awt.Color;
import java.awt.Graphics;

import javafx.scene.shape.Circle;

public class Object {
	
public static int maskx,masky,mdiam;
	
	protected double x;
	protected double y;
	protected int diam;
	
	protected Color color;
	
	public Object(int x, int y, int diam, Color color) {
		this.x = x;
		this.y = y;
		this.diam = diam;
		this.color = color;
		
		Object.maskx = diam/2;
		Object.masky = diam/2;
		Object.mdiam = diam;
	}
	
	public int getX() {
		return (int)this.x;
	}
	
	public int getY() {
		return (int)this.y;
	}
	
	public int getDiam() {
		return this.diam;
	}

	public void tick() {
		
	}
	
	public double calculateDistance(int x1, int y1, int x2, int y2) {
		return Math.sqrt((x1 - x2) * (x1 - x2) + (y1 - y2) * (y1 - y2));
	}
	
	public static boolean isColliding(Object e1, Object e2) {		
		if((e1.getX()+e1.getDiam()/2 != e2.getX()+e2.getDiam()/2) && (e1.getX()-e1.getDiam()/2 != e2.getX()-e2.getDiam()/2) && (e1.getY()+e1.getDiam()/2 != e2.getY()+e2.getDiam()/2) && (e1.getY()-e1.getDiam()/2 != e2.getY()-e2.getDiam()/2)) {
			return false;
		}else {
			return true;
		}
	}
	
	public static boolean isFree(Object e1, Object e2) {		
		if((e1.getX()+e1.getDiam()/2 != e2.getX()+e2.getDiam()/2) && (e1.getX()-e1.getDiam()/2 != e2.getX()-e2.getDiam()/2) && (e1.getY()+e1.getDiam()/2 != e2.getY()+e2.getDiam()/2) && (e1.getY()-e1.getDiam()/2 != e2.getY()-e2.getDiam()/2)) {
			return false;
		}else {
			return true;
		}
	}
	
	public void render(Graphics g) {
		g.setColor(color);
		g.fillOval(getX()-(diam/2), getY()-(diam/2), diam, diam);
	}
	
	public void setX(int newX) {
		this.x = newX;
	}
	
	public void setY(int newY) {
		this.y = newY;
	}

}
